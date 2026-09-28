package org.projecteden.farmermobile.data.repository

import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import org.projecteden.farmermobile.data.local.FarmDao
import org.projecteden.farmermobile.data.model.AdviceEntity
import org.projecteden.farmermobile.data.model.AdviceHistoryEntity
import org.projecteden.farmermobile.data.model.FarmProfileEntity
import org.projecteden.farmermobile.data.remote.EdenApiClient
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Offline-first repository coordinating Room database cache and remote API.
 * Room remains the primary read source.
 *
 * Backend Contract Note:
 * The current server API (services/api/src/server.ts) supports:
 * - GET /api/v1/overview
 * - POST /api/v1/advice
 * Endpoint gaps:
 * - /api/v1/farmer-profile (Profile persistence is not yet provided by API; maintained in local Room)
 * - /api/v1/advice-history (History persistence is not yet provided by API; maintained in local Room)
 */
class FarmerRepository(
    private val farmDao: FarmDao,
    private val apiClient: EdenApiClient = EdenApiClient()
) {

    val farmProfile: Flow<FarmProfileEntity> = farmDao.getFarmProfile().map {
        it ?: FarmProfileEntity()
    }

    val currentAdvice: Flow<AdviceEntity> = farmDao.getAdvice().map {
        it ?: AdviceEntity()
    }

    val adviceHistory: Flow<List<AdviceHistoryEntity>> = farmDao.getAdviceHistory().map { list ->
        if (list.isEmpty()) listOf(AdviceHistoryEntity()) else list
    }

    suspend fun refreshAdvice(): Result<Boolean> {
        val remoteResult = apiClient.fetchAdvice()
        val timeFormat = SimpleDateFormat("h:mm a", Locale.getDefault())
        val formattedTime = "আজ " + timeFormat.format(Date())

        return if (remoteResult.isSuccess) {
            val remote = remoteResult.getOrNull()
            val current = AdviceEntity(
                isOffline = false,
                lastSyncFormatted = formattedTime,
                cacheTimeString = "$formattedTime সিঙ্ক",
                updatedAt = System.currentTimeMillis()
            )
            farmDao.insertOrUpdateAdvice(current)
            Result.success(true)
        } else {
            // Keep existing cache, mark offline status
            val cached = AdviceEntity(
                isOffline = true,
                lastSyncFormatted = formattedTime,
                cacheTimeString = "$formattedTime অফলাইন ক্যাশে",
                updatedAt = System.currentTimeMillis()
            )
            farmDao.insertOrUpdateAdvice(cached)
            Result.failure(remoteResult.exceptionOrNull() ?: Exception("অফলাইন মোড: সার্ভারের সাথে যোগাযোগ করা যায়নি"))
        }
    }

    suspend fun saveProfile(profile: FarmProfileEntity) {
        val updated = profile.copy(
            lastUpdatedFormatted = SimpleDateFormat("h:mm a", Locale.getDefault()).format(Date()),
            lastUpdatedTimestamp = System.currentTimeMillis()
        )
        farmDao.insertOrUpdateProfile(updated)
    }

    suspend fun markAudioListened(historyId: String) {
        farmDao.insertHistoryItem(
            AdviceHistoryEntity(
                id = historyId,
                hasListenedAudio = true
            )
        )
    }
}
