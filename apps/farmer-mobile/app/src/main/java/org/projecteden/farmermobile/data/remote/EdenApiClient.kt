package org.projecteden.farmermobile.data.remote

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL

/** The server's farmer card for the top-ranked rotation (see FarmerCard in packages/contracts). */
data class RemoteAdviceResponse(
    val unionId: String,
    val unionNameBangla: String,
    val releaseId: String,
    val rotationTitle: String,
    val rotationSubtitle: String,
    val season1Name: String,
    val season1Variety: String,
    val season1Window: String,
    val season1Stage: String,
    val season1Irrigation: String,
    val season2Name: String,
    val season2Variety: String,
    val season2Window: String,
    val season2Notes: String,
    val season2Fertilizer: String,
    val alternativeName: String,
    val alternativeCategory: String,
    val alternativeSowing: String,
    val alternativeYield: String,
    val alternativeMarketPrice: String,
    val narrative: String,
    val provenance: String,
    val audioScript: String,
    val audioDurationSeconds: Int,
    val rawJson: String
)

data class RemoteOverviewResponse(
    val district: String,
    val upazila: String,
    val union: String,
    val season: String,
    val rainLast30dMm: Double,
    val rootzoneMoisture: Double,
    val rootzoneMoistureDate: String,
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
                val smap = satellite?.optJSONObject("smap")
                val rain = satellite?.optJSONObject("rain_last_30_days")
                val alerts = json.optJSONArray("active_alerts")
                val firstAlert = alerts?.optJSONObject(0)?.optString("titleBangla")

                Result.success(
                    RemoteOverviewResponse(
                        district = scope?.optString("district") ?: "Rajshahi",
                        upazila = scope?.optString("upazila") ?: "Tanore",
                        union = scope?.optString("union") ?: "Talanda",
                        season = seasonSummary?.optString("season") ?: "Aman 2026",
                        rainLast30dMm = rain?.optDouble("imergLateMm") ?: Double.NaN,
                        rootzoneMoisture = smap?.optDouble("rootZoneM3M3") ?: Double.NaN,
                        rootzoneMoistureDate = smap?.optString("date").orEmpty(),
                        activeAlertBangla = firstAlert
                    )
                )
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
                val card = json.getJSONObject("farmer_card")
                val season1 = card.getJSONObject("season1")
                val season2 = card.getJSONObject("season2")
                val alternative = card.getJSONObject("alternative")

                Result.success(
                    RemoteAdviceResponse(
                        unionId = scope?.optString("union_id") ?: "talanda_tanore",
                        unionNameBangla = scope?.optString("union_name_bangla") ?: "তালন্দ ইউনিয়ন",
                        releaseId = json.optString("data_release"),
                        rotationTitle = card.getString("rotationTitleBangla"),
                        rotationSubtitle = card.getString("rotationSubtitleBangla"),
                        season1Name = season1.getString("name"),
                        season1Variety = season1.getString("variety"),
                        season1Window = season1.getString("windowBangla"),
                        season1Stage = season1.getString("stageBangla"),
                        season1Irrigation = season1.getString("irrigationBangla"),
                        season2Name = season2.getString("name"),
                        season2Variety = season2.getString("variety"),
                        season2Window = season2.getString("windowBangla"),
                        season2Notes = season2.getString("notesBangla"),
                        season2Fertilizer = season2.getString("fertilizerBangla"),
                        alternativeName = alternative.getString("name"),
                        alternativeCategory = alternative.getString("categoryBangla"),
                        alternativeSowing = alternative.getString("sowingBangla"),
                        alternativeYield = alternative.getString("yieldBangla"),
                        alternativeMarketPrice = alternative.getString("marketPriceBangla"),
                        narrative = card.getString("narrativeBangla"),
                        provenance = card.getString("provenanceBangla"),
                        audioScript = card.getString("audioScriptBangla"),
                        audioDurationSeconds = card.optInt("audioDurationSeconds", 30),
                        rawJson = body
                    )
                )
            } else {
                Result.failure(Exception("HTTP error code $code"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
