import java.net.HttpURLConnection
import java.net.URL

def logInfo  = { String msg -> try { log?.info(msg)  ?: println("INFO  " + msg) } catch (ignored) { println("INFO  " + msg) } }
def logError = { String msg, Throwable t = null ->
  try { if (log != null) { if (t != null) log.error(msg, t) else log.error(msg) } else println("ERROR " + msg) }
  catch (ignored) { println("ERROR " + msg) }
}

def cfgVal = { String key ->
  try { return configuration[key] } catch (ignored) {
    try { return configuration.getAt(key) } catch (ignored2) { return null }
  }
}
def cfgStr = { String key ->
  def v = cfgVal(key)
  def s = (v == null) ? null : "${v}".trim()
  if (!s) throw new IllegalArgumentException("Missing required configuration property: ${key}")
  return s
}

try {
  def serviceAddress = cfgStr("serviceAddress")
  def url = "${serviceAddress}/health"
  logInfo("Testing facade: GET ${url}")

  HttpURLConnection conn = (HttpURLConnection) new URL(url).openConnection()
  conn.setRequestMethod("GET")
  conn.setConnectTimeout(5000)
  conn.setReadTimeout(5000)
  int status = conn.getResponseCode()

  if (status < 200 || status >= 300) {
    throw new RuntimeException("Facade health check failed (${status})")
  }

  logInfo("Facade health check OK (status=${status}).")
  return true

} catch (Throwable t) {
  logError("TestScript failed: ${t.getMessage()}", t)
  throw t
}
