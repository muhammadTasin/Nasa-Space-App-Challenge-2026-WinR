package org.projecteden.farmermobile.data.remote

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL

data class RemoteAdviceResponse(
    val unionId: String,
    val unionNameBangla: String,
    val recommendedCropName: String,
    val recommendedCropVariety: String,
    val nextCropName: String,
    val nextCropVariety: String,
    val fieldFreeDateBangla: String,
    val rescueIrrigationRequired: String,
    val waterSavings: String,
    val rawJson: String
)

data class RemoteOverviewResponse(
    val district: String,
    val upazila: String,
    val union: String,
    val season: String,
    val rainLast7d: Double,
    val rootzoneMoisture: Double,
    val activeAlertBangla: String?
)

/**
 * Lightweight, zero-dependency HTTP client using Android built-in HttpURLConnection.
 * Targets the shared Node/TypeScript backend at port 4000.
 */
class EdenApiClient(
    // 10.0.2.2 is Android emulator's loopback to host localhost
    private val baseUrl: String = "http://10.0.2.2:4000"
) {

    suspend fun fetchOverview(): Result<RemoteOverviewResponse> = withContext(Dispatchers.IO) {
        try {
            val url = URL("$baseUrl/api/v1/overview")
            val conn = (url.openConnection() as HttpURLConnection).apply {
                requestMethod = "GET"
                connectTimeout = 3000
                readTimeout = 4000
                setRequestProperty("Accept", "application/json")
            }

            val code = conn.responseCode
            if (code in 200..299) {
                val reader = BufferedReader(InputStreamReader(conn.inputStream))
                val body = reader.readText()
                reader.close()

                val json = JSONObject(body)
                val scope = json.optJSONObject("scope")
                val seasonSummary = json.optJSONObject("season_summary")
                val satellite = json.optJSONObject("local_satellite_conditions")
                val alerts = json.optJSONArray("active_alerts")
                val firstAlert = if (alerts != null && alerts.length() > 0) {
                    val alertObj = alerts.getJSONObject(0)
                    if (alertObj.has("titleBangla")) alertObj.getString("titleBangla") else null
                } else null

                val resp = RemoteOverviewResponse(
                    district = scope?.optString("district") ?: "Rajshahi",
                    upazila = scope?.optString("upazila") ?: "Tanore",
                    union = scope?.optString("union") ?: "Talanda",
                    season = seasonSummary?.optString("season") ?: "Aman 2026",
                    rainLast7d = satellite?.optDouble("imerg_rain_last_7d_mm") ?: 0.0,
                    rootzoneMoisture = satellite?.optDouble("smap_rootzone_moisture") ?: 0.0,
                    activeAlertBangla = firstAlert
                )
                Result.success(resp)
            } else {
                Result.failure(Exception("HTTP error code $code"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun fetchAdvice(
        landType: String = "medium_high",
        waterWeight: Double = 0.5,
        incomeWeight: Double = 0.3,
        soilWeight: Double = 0.2
    ): Result<RemoteAdviceResponse> = withContext(Dispatchers.IO) {
        try {
            val url = URL("$baseUrl/api/v1/advice")
            val conn = (url.openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                connectTimeout = 3000
                readTimeout = 4000
                doOutput = true
                setRequestProperty("Content-Type", "application/json")
                setRequestProperty("Accept", "application/json")
            }

            val payload = JSONObject().apply {
                put("unionId", "talanda_tanore")
                put("landType", landType)
                put("farmerPriorities", JSONObject().apply {
                    put("water", waterWeight)
                    put("income", incomeWeight)
                    put("soil", soilWeight)
                })
            }

            val writer = OutputStreamWriter(conn.outputStream)
            writer.write(payload.toString())
            writer.flush()
            writer.close()

            val code = conn.responseCode
            if (code in 200..299) {
                val reader = BufferedReader(InputStreamReader(conn.inputStream))
                val body = reader.readText()
                reader.close()

                val json = JSONObject(body)
                val scope = json.optJSONObject("scope")
                val options = json.optJSONArray("options")
                val firstOption = options?.optJSONObject(0)

                val resp = RemoteAdviceResponse(
                    unionId = scope?.optString("union_id") ?: "talanda_tanore",
                    unionNameBangla = scope?.optString("union_name_bangla") ?: "তালন্দ ইউনিয়ন",
                    recommendedCropName = "আমন ধান",
                    recommendedCropVariety = "ব্রি ধান-৪৯",
                    nextCropName = "সরিষা",
                    nextCropVariety = "বারি সরিষা-১৪",
                    fieldFreeDateBangla = firstOption?.optString("fieldFreeDateBangla") ?: "১০ নভেম্বর",
                    rescueIrrigationRequired = "৭/২৫ মৌসুম",
                    waterSavings = "৫৯৮ মিমি",
                    rawJson = body
                )
                Result.success(resp)
            } else {
                Result.failure(Exception("HTTP error code $code"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
