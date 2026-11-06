/*
 * Corrector de etiquetas ZPL (Mercado Libre → Zebra ZD220 100×190 mm).
 *
 * Trabaja sobre los BYTES del archivo (Uint8Array), nunca sobre texto decodificado:
 * así el resultado es idéntico al original salvo los bytes de los dos reemplazos,
 * sin importar la codificación (UTF-8, Latin-1, CP1252) ni los saltos de línea.
 * Todo corre en el navegador: el archivo no se sube al servidor.
 *
 * Reemplazos (solo comandos completos: el byte siguiente no puede ser un dígito,
 * así ^LH0,900 o ^LH0,4100 no se tocan):
 *   ^LH0,90  → ^LH0,0
 *   ^LH0,410 → ^LH0,320
 * Se hace en una sola pasada y los resultados no vuelven a coincidir con ningún
 * patrón, por lo que es idempotente.
 */
(function (global) {
  'use strict';

  function ascii(s) {
    var a = new Uint8Array(s.length);
    for (var i = 0; i < s.length; i++) a[i] = s.charCodeAt(i);
    return a;
  }

  var REEMPLAZOS = [
    { id: 'lh90',  buscar: '^LH0,90',  reemplazo: '^LH0,0' },
    { id: 'lh410', buscar: '^LH0,410', reemplazo: '^LH0,320' }
  ];
  REEMPLAZOS.forEach(function (r) { r.b = ascii(r.buscar); r.r = ascii(r.reemplazo); });
  var YA_OK = { lh90: ascii('^LH0,0'), lh410: ascii('^LH0,320') };
  var XA = ascii('^XA'), XZ = ascii('^XZ');
  var CARET = 0x5E; // '^'

  function esDigito(b) { return b >= 0x30 && b <= 0x39; }

  function coincide(bytes, pos, pat) {
    if (pos + pat.length > bytes.length) return false;
    for (var k = 0; k < pat.length; k++) if (bytes[pos + k] !== pat[k]) return false;
    return true;
  }

  // Comando completo: coincide y lo que sigue NO es un dígito (o es fin de archivo).
  function coincideCompleto(bytes, pos, pat) {
    if (!coincide(bytes, pos, pat)) return false;
    var sig = pos + pat.length;
    return sig >= bytes.length || !esDigito(bytes[sig]);
  }

  // Devuelve un mensaje de error si la codificación no se puede procesar byte a byte.
  function problemaCodificacion(bytes) {
    if (bytes.length >= 2 && ((bytes[0] === 0xFF && bytes[1] === 0xFE) || (bytes[0] === 0xFE && bytes[1] === 0xFF)))
      return 'El archivo está en UTF-16 (tiene marca BOM de UTF-16). Los ZPL de Mercado Libre vienen en ASCII/UTF-8; volvé a descargarlo desde Mercado Libre sin abrirlo ni guardarlo con otro programa.';
    var n = Math.min(bytes.length, 4096), nulos = 0;
    for (var i = 0; i < n; i++) if (bytes[i] === 0) nulos++;
    if (n > 0 && nulos / n > 0.1)
      return 'El archivo parece estar en UTF-16/UTF-32 (muchos bytes nulos). No se puede corregir sin riesgo de corromperlo; volvé a descargarlo desde Mercado Libre.';
    return null;
  }

  function finDeLinea(bytes) {
    var crlf = 0, lf = 0, cr = 0;
    for (var i = 0; i < bytes.length; i++) {
      if (bytes[i] === 0x0D) { if (bytes[i + 1] === 0x0A) { crlf++; i++; } else cr++; }
      else if (bytes[i] === 0x0A) lf++;
    }
    var tipos = [];
    if (crlf) tipos.push('Windows (CRLF)');
    if (lf) tipos.push('Unix (LF)');
    if (cr) tipos.push('Mac antiguo (CR)');
    return tipos.length ? tipos.join(' + ') : 'sin saltos de línea';
  }

  /*
   * corregir(bytes: Uint8Array) → {
   *   ok, error, salida: Uint8Array, etiquetas, cierres, reemplazos: {lh90, lh410}, total,
   *   yaCorregidas, incompletas: [nº de etiqueta], fueraDeEtiqueta, avisos: [], finDeLinea
   * }
   */
  function corregir(bytes) {
    var res = {
      ok: false, error: null, salida: bytes, etiquetas: 0, cierres: 0,
      reemplazos: { lh90: 0, lh410: 0 }, total: 0, yaCorregidas: 0,
      incompletas: [], fueraDeEtiqueta: 0, avisos: [], finDeLinea: ''
    };
    if (!bytes || bytes.length === 0) { res.error = 'El archivo está vacío.'; return res; }
    var vacio = true;
    for (var v = 0; v < bytes.length; v++) {
      var c = bytes[v];
      if (c !== 0x20 && c !== 0x09 && c !== 0x0A && c !== 0x0D) { vacio = false; break; }
    }
    if (vacio) { res.error = 'El archivo solo contiene espacios o saltos de línea.'; return res; }
    var enc = problemaCodificacion(bytes);
    if (enc) { res.error = enc; return res; }

    // Estado por etiqueta: índice 0 = contenido antes del primer ^XA.
    var est = [{ lh90: 0, lh410: 0, ok90: 0, ok410: 0 }];
    var trozos = [], desde = 0, largo = 0;
    var i = 0, n = bytes.length;
    while (i < n) {
      if (bytes[i] !== CARET) { i++; continue; }
      var actual = est[est.length - 1];
      if (coincide(bytes, i, XA)) {
        res.etiquetas++;
        est.push({ lh90: 0, lh410: 0, ok90: 0, ok410: 0 });
        i += XA.length; continue;
      }
      if (coincide(bytes, i, XZ)) { res.cierres++; i += XZ.length; continue; }
      var hecho = false;
      for (var r = 0; r < REEMPLAZOS.length; r++) {
        var R = REEMPLAZOS[r];
        if (coincideCompleto(bytes, i, R.b)) {
          trozos.push(bytes.subarray(desde, i), R.r);
          largo += (i - desde) + R.r.length;
          i += R.b.length; desde = i;
          res.reemplazos[R.id]++;
          actual[R.id]++;
          if (est.length === 1) res.fueraDeEtiqueta++;
          hecho = true; break;
        }
      }
      if (hecho) continue;
      if (coincideCompleto(bytes, i, YA_OK.lh90)) actual.ok90++;
      else if (coincideCompleto(bytes, i, YA_OK.lh410)) actual.ok410++;
      i++;
    }
    trozos.push(bytes.subarray(desde, n));
    largo += n - desde;

    if (res.etiquetas === 0) {
      res.error = 'No se encontraron comandos ZPL reconocibles (ningún ^XA). Verificá que sea el archivo de etiquetas descargado de Mercado Libre.';
      return res;
    }

    var salida = new Uint8Array(largo), p = 0;
    trozos.forEach(function (t) { salida.set(t, p); p += t.length; });
    res.salida = salida;
    res.total = res.reemplazos.lh90 + res.reemplazos.lh410;

    for (var e = 1; e < est.length; e++) {
      var s = est[e];
      var tiene90 = s.lh90 + s.ok90 > 0, tiene410 = s.lh410 + s.ok410 > 0;
      if (!(tiene90 && tiene410)) res.incompletas.push(e);
      else if (s.lh90 + s.lh410 === 0) res.yaCorregidas++;
    }

    if (res.cierres !== res.etiquetas)
      res.avisos.push('Hay ' + res.etiquetas + ' aperturas ^XA y ' + res.cierres + ' cierres ^XZ. El archivo podría estar incompleto; igual se conserva tal cual.');
    if (res.fueraDeEtiqueta)
      res.avisos.push(res.fueraDeEtiqueta + ' reemplazo(s) estaban antes del primer ^XA (fuera de una etiqueta).');
    if (coincide(bytes, 0, ascii('\xEF\xBB\xBF')))
      res.avisos.push('El archivo empieza con marca BOM UTF-8; se conserva sin cambios.');
    var txt = '';
    for (var t = 0; t < Math.min(n, 2000000); t++) {
      if ((bytes[t] === 0x5E || bytes[t] === 0x7E) && bytes[t + 1] === 0x43 && bytes[t + 2] === 0x43) { txt = 'cc'; break; }
    }
    if (txt) res.avisos.push('El archivo usa ^CC/~CC (cambio del carácter de comando): los comandos escritos con otro prefijo no se detectan.');
    res.finDeLinea = finDeLinea(bytes);
    res.ok = true;
    return res;
  }

  function nombreCorregido(nombre) {
    var m = /^(.*)(\.[^.\/\\]+)$/.exec(nombre || '');
    if (!m || !m[1]) return (nombre || 'etiquetas') + '_corregido';
    return m[1] + '_corregido' + m[2];
  }

  function extensionValida(nombre) {
    return /\.(zpl|txt)$/i.test(nombre || '');
  }

  // Texto solo para la vista previa (nunca para la descarga).
  function textoVista(bytes, max) {
    var s;
    try { s = new TextDecoder('utf-8', { fatal: true }).decode(bytes); }
    catch (e) { s = new TextDecoder('windows-1252').decode(bytes); }
    return max && s.length > max ? s.slice(0, max) : s;
  }

  global.ZPLCorrector = {
    corregir: corregir,
    nombreCorregido: nombreCorregido,
    extensionValida: extensionValida,
    textoVista: textoVista,
    REEMPLAZOS: REEMPLAZOS.map(function (r) { return { buscar: r.buscar, reemplazo: r.reemplazo }; })
  };
})(typeof window !== 'undefined' ? window : this);
