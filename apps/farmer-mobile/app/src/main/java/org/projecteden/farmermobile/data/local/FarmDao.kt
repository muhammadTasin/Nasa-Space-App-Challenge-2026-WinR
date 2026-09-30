package org.projecteden.farmermobile.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow
import org.projecteden.farmermobile.data.model.AdviceEntity
import org.projecteden.farmermobile.data.model.AdviceHistoryEntity
import org.projecteden.farmermobile.data.model.FarmProfileEntity

@Dao
interface FarmDao {
    @Query("SELECT * FROM farm_profile WHERE id = 'primary_pilot_farm' LIMIT 1")
    fun getFarmProfile(): Flow<FarmProfileEntity?>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertOrUpdateProfile(profile: FarmProfileEntity)

    @Query("SELECT * FROM cached_advice WHERE id = 'current_seasonal_advice' LIMIT 1")
    fun getAdvice(): Flow<AdviceEntity?>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertOrUpdateAdvice(advice: AdviceEntity)

    @Query("SELECT * FROM advice_history ORDER BY createdAt DESC")
    fun getAdviceHistory(): Flow<List<AdviceHistoryEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertHistoryItem(item: AdviceHistoryEntity)

    @Query("UPDATE advice_history SET hasListenedAudio = 1 WHERE id = :historyId")
    suspend fun markHistoryItemListened(historyId: String)
}
