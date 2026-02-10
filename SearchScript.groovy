import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import groovy.json.JsonSlurper

import org.identityconnectors.framework.common.objects.*
import org.identityconnectors.framework.common.objects.filter.Filter
import org.identityconnectors.framework.common.objects.filter.EqualsFilter
import org.identityconnectors.framework.common.objects.filter.AndFilter
import org.identityconnectors.framework.common.exceptions.ConnectorException
import org.identityconnectors.framework.common.objects.AttributeUtil

def SCRIPT_VERSION = "2026-02-04-search-facade-alumnos-matriculas-v1-sanitized-gstring"

// -------------------- logging helpers --------------------
def logInfo  = { String msg -> try { log?.info(msg)  ?: println("INFO  " + msg) } catch (ignored) { println("INFO  " + msg) } }
def logDebug = { String msg -> try { log?.debug(msg) ?: println("DEBUG " + msg) } catch (ignored) { println("DEBUG " + msg) } }
def logWarn  = { String msg -> try { log?.warn(msg)  ?: println("WARN  " + msg) } catch (ignored) { println("WARN  " + msg) } }
def logError = { String msg, Throwable t = null ->
    try {
        if (log != null) {
            if (t != null) log.error(msg, t) else log.error(msg)
        } else {
            println("ERROR " + msg + (t != null ? ("\n" + t.toString()) : ""))
        }
    } catch (ignored) {
        println("ERROR " + msg + (t != null ? ("\n" + t.toString()) : ""))
    }
}

// -------------------- safe string conversion (NO GString) --------------------
def toJString = { def v ->
    if (v == null) return null
    // Ensure java.lang.String, not GStringImpl
    return (v instanceof String) ? (String) v : v.toString()
}
def trimToNull = { def v ->
    def s = toJString(v)
    if (s == null) return null
    s = s.trim()
    return s.isEmpty() ? null : s
}

// -------------------- configuration helpers --------------------
def cfgVal = { String key ->
    try { return configuration[key] } catch (ignored) {
        try { return configuration.getAt(key) } catch (ignored2) { return null }
    }
}
def cfgStr = { String key, boolean required = true ->
    def s = trimToNull(cfgVal(key))
    if (!s) {
        if (required) throw new IllegalArgumentException("Missing required configuration property: " + key)
        return null
    }
    return s
}
def cfgInt = { String key, int defaultValue ->
    def v = cfgVal(key)
    if (v == null) return defaultValue
    try {
        def s = trimToNull(v)
        if (!s) return defaultValue
        return Integer.parseInt(s)
    } catch (ignored) {
        return defaultValue
    }
}
def cfgBool = { String key, boolean defaultValue ->
    def v = cfgVal(key)
    if (v == null) return defaultValue
    def s = trimToNull(v)
    if (!s) return defaultValue
    return Boolean.valueOf(s)
}

// -------------------- filter parsing --------------------
def extractIdAlumnoFromFilter
extractIdAlumnoFromFilter = { Filter f ->
    if (f == null) return null

    if (f instanceof EqualsFilter) {
        def attr = f.getAttribute()
        def name = attr?.getName()
        def val = (attr != null) ? AttributeUtil.getSingleValue(attr) : null
        logDebug("Filter EqualsFilter on '" + name + "' value='" + toJString(val) + "'")

        if (name != null && (
                name.equalsIgnoreCase("__UID__") ||
                name.equalsIgnoreCase("__NAME__") ||
                name.equalsIgnoreCase("idAlumno") ||
                name.equalsIgnoreCase("frIndexedString4")
        )) {
            return trimToNull(val)
        }
    }

    if (f instanceof AndFilter) {
        def subs = f.getFilters()
        logDebug("Filter AndFilter with " + (subs?.size() ?: 0) + " subfilters")
        for (def sub : subs) {
            def candidate = extractIdAlumnoFromFilter(sub)
            if (candidate != null) return candidate
        }
    }

    return null
}

// -------------------- header parsing (optional) --------------------
def normalizeHeaderToken = { String s ->
    if (s == null) return null
    def t = s.trim()
    if (t.startsWith("[")) t = t.substring(1).trim()
    if (t.endsWith("]")) t = t.substring(0, t.length() - 1).trim()
    return t
}

def parseHeaderLine = { String line ->
    if (line == null) return null
    def s = line.trim()
    if (s.isEmpty()) return null

    String name
    String value

    if (s.contains(":")) {
        def parts = s.split(":", 2)
        name = parts[0]; value = (parts.length > 1) ? parts[1] : ""
    } else if (s.contains("=")) {
        def parts = s.split("=", 2)
        name = parts[0]; value = (parts.length > 1) ? parts[1] : ""
    } else {
        return null
    }

    name = normalizeHeaderToken(name)
    value = normalizeHeaderToken(value)
    if (!name) return null
    return [name: name.trim(), value: (value ?: "").trim()]
}

def expandHeaderLines = { def hdrs ->
    if (hdrs == null) return []
    if (hdrs instanceof Collection) {
        return hdrs.collect { it == null ? null : trimToNull(it) }.findAll { it }
    }
    def s = trimToNull(hdrs)
    if (!s) return []
    if (s.startsWith("[") && s.endsWith("]") && s.contains(",")) {
        def inner = s.substring(1, s.length() - 1)
        return inner.split(/\s*,\s*/).collect { it.trim() }.findAll { it }
    }
    return [s]
}

def applyDefaultHeaders = { HttpURLConnection conn ->
    def hdrs = cfgVal("defaultRequestHeaders")
    def lines = expandHeaderLines(hdrs)
    for (def line : lines) {
        def parsed = parseHeaderLine(line)
        if (parsed == null) continue
        conn.setRequestProperty(parsed.name, parsed.value)
        logDebug("Applied header '" + parsed.name + "'='" + parsed.value + "'")
    }
}

// -------------------- HTTP GET --------------------
def httpGet = { String urlString, int connectTimeoutMs, int readTimeoutMs ->
    logInfo("HTTP GET " + urlString + " (connectTimeoutMs=" + connectTimeoutMs + ", readTimeoutMs=" + readTimeoutMs + ")")

    HttpURLConnection conn = (HttpURLConnection) new URL(urlString).openConnection()
    conn.setRequestMethod("GET")
    conn.setConnectTimeout(connectTimeoutMs)
    conn.setReadTimeout(readTimeoutMs)

    applyDefaultHeaders(conn)
    if (conn.getRequestProperty("Accept") == null) {
        conn.setRequestProperty("Accept", "application/json")
    }

    int status = conn.getResponseCode()
    InputStream is = (status >= 200 && status < 300) ? conn.getInputStream() : conn.getErrorStream()
    String body = (is != null) ? is.getText("UTF-8") : ""

    int bytes = 0
    try { bytes = (body == null) ? 0 : body.getBytes("UTF-8").length } catch (ignored) { bytes = 0 }
    logInfo("HTTP response status=" + status + ", bytes=" + bytes)

    return [status: status, body: body]
}

// -------------------- emit result --------------------
def emit = { ConnectorObject obj ->
    if (binding?.hasVariable("handler") && handler != null) {
        handler.call(obj)
        return
    }
    if (binding?.hasVariable("results") && results instanceof List) {
        results.add(obj)
        return
    }
    throw new ConnectorException("No handler/results available to emit search results.")
}

// -------------------- mapping helpers --------------------
def safeStr = { def v -> trimToNull(v) }  // <- always java.lang.String or null

def addIfPresent = { ConnectorObjectBuilder b, String name, def value ->
    def s = safeStr(value)
    if (s != null) {
        b.addAttribute(AttributeBuilder.build(name, s)) // s is java.lang.String
    }
}

def buildAlumnoObject = { String idAlumno, Map alumno ->
    def idS = trimToNull(idAlumno)
    def b = new ConnectorObjectBuilder()
    b.setObjectClass(new ObjectClass("alumnos"))
    b.setUid(idS)
    b.setName(idS)

    addIfPresent(b, "IdAlumno", alumno.get("IdAlumno"))
    addIfPresent(b, "Nombre", alumno.get("Nombre"))
    addIfPresent(b, "Apellidos", alumno.get("Apellidos"))
    addIfPresent(b, "EmailPersonal", alumno.get("EmailPersonal"))
    addIfPresent(b, "IdSeguridad", alumno.get("IdSeguridad"))
    addIfPresent(b, "Telefono", alumno.get("Telefono"))
    addIfPresent(b, "IdPais", alumno.get("IdPais"))

    return b.build()
}

def buildMatriculaObject = { Map m ->
    // UID strategy: IdIntegracionMatricula (fallback UNKNOWN)
    def uid = safeStr(m.get("IdIntegracionMatricula"))
    if (uid == null) uid = "UNKNOWN"

    def b = new ConnectorObjectBuilder()
    b.setObjectClass(new ObjectClass("matriculas"))
    b.setUid(uid)
    b.setName(uid)

    addIfPresent(b, "IdIntegracionMatricula", m.get("IdIntegracionMatricula"))
    addIfPresent(b, "IdPlan", m.get("IdPlan"))
    addIfPresent(b, "cEstadoMatricula", m.get("cEstadoMatricula"))
    addIfPresent(b, "EstadoMatriculaNombre", m.get("EstadoMatriculaNombre"))
    addIfPresent(b, "sEstadoMatricula", m.get("sEstadoMatricula"))

    addIfPresent(b, "IdAlumno", m.get("IdAlumno"))
    addIfPresent(b, "TipoDocumento", m.get("TipoDocumento"))
    addIfPresent(b, "NumeroDocumento", m.get("NumeroDocumento"))

    return b.build()
}


// -------------------- main --------------------
try {
    def ocVal = objectClass?.getObjectClassValue()
    logInfo("SearchScript (" + SCRIPT_VERSION + ") starting. objectClass='" + ocVal + "' filter='" + toJString(filter) + "'")
    logDebug("Binding variables: " + (binding?.variables?.keySet()?.sort() ?: []))

    if (objectClass == null) return

    // supported object types
    def supported = ["alumnos", "matriculas", "__ACCOUNT__", ObjectClass.ACCOUNT_NAME]
    if (!supported.any { it.equalsIgnoreCase(ocVal) }) {
        logWarn("Unsupported objectClass='" + ocVal + "'. Supported: alumnos, matriculas. Returning no results.")
        return
    }

    def serviceAddress = cfgStr("serviceAddress", true)  // e.g. http://localhost:8090
    def connectTimeoutMs = cfgInt("connectTimeoutMs", 10000)
    def readTimeoutMs = cfgInt("readTimeoutMs", 20000)

    def idAlumno = extractIdAlumnoFromFilter(filter)
    logInfo("Resolved idAlumno='" + idAlumno + "' from filter")
    if (idAlumno == null) return

    def encoded = URLEncoder.encode(idAlumno, "UTF-8")
    def slurper = new JsonSlurper()

    if ("alumnos".equalsIgnoreCase(ocVal) || "__ACCOUNT__".equalsIgnoreCase(ocVal) || ObjectClass.ACCOUNT_NAME.equalsIgnoreCase(ocVal)) {
        def url = serviceAddress + "/aic/alumnos?idAlumno=" + encoded
        def resp = httpGet(url, connectTimeoutMs, readTimeoutMs)

        if (resp.status == 404) return
        if (resp.status < 200 || resp.status >= 300) {
            logError("Facade call failed status=" + resp.status + ". Body (truncated)='" + (resp.body?.take(800) ?: "") + "'")
            throw new ConnectorException("Facade call failed (" + resp.status + "). Body: " + (resp.body ?: ""))
        }

        def parsed = slurper.parseText(resp.body ?: "{}")
        if (!(parsed instanceof Map)) {
            throw new ConnectorException("Unexpected alumnos response (expected JSON object).")
        }

        def obj = buildAlumnoObject(idAlumno, (Map) parsed)
        emit(obj)
        return
    }

    if ("matriculas".equalsIgnoreCase(ocVal)) {
        def onlyActiveBool = cfgBool("onlyActive", true)
        def pageIndex = cfgInt("pageIndex", 1)
        def itemsPerPage = cfgInt("itemsPerPage", 50)

        def url = serviceAddress + "/aic/matriculas?idAlumno=" + encoded +
                "&onlyActive=" + (onlyActiveBool ? "true" : "false") +
                "&pageIndex=" + pageIndex +
                "&itemsPerPage=" + itemsPerPage

        def resp = httpGet(url, connectTimeoutMs, readTimeoutMs)

        if (resp.status == 404) return
        if (resp.status < 200 || resp.status >= 300) {
            logError("Facade call failed status=" + resp.status + ". Body (truncated)='" + (resp.body?.take(800) ?: "") + "'")
            throw new ConnectorException("Facade call failed (" + resp.status + "). Body: " + (resp.body ?: ""))
        }

        def parsed = slurper.parseText(resp.body ?: "[]")
        if (!(parsed instanceof List)) {
            throw new ConnectorException("Unexpected matriculas response (expected JSON array).")
        }

        for (def item : (List) parsed) {
            if (!(item instanceof Map)) continue
            def obj = buildMatriculaObject((Map) item)
            emit(obj)
        }
        return
    }

} catch (Throwable t) {
    logError("SearchScript failed: " + t.getClass().getName() + ": " + t.getMessage(), t)
    throw t
}
