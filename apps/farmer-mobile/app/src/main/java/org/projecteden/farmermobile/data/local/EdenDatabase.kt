package org.projecteden.farmermobile.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.sqlite.db.SupportSQLiteDatabase
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import org.projecteden.farmermobile.data.model.AdviceEntity
import org.projecteden.farmermobile.data.model.AdviceHistoryEntity
import org.projecteden.farmermobile.data.model.FarmProfileEntity

@Database(
    entities = [
        FarmProfileEntity::class,
        AdviceEntity::class,
        AdviceHistoryEntity::class
    ],
    version = 1,
    exportSchema = false
)
abstract class EdenDatabase : RoomDatabase() {
    abstract fun farmDao(): FarmDao

    companion object {
        @Volatile
        private var INSTANCE: EdenDatabase? = null

        fun getInstance(context: Context): EdenDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    EdenDatabase::class.java,
                    "eden_farmer.db"
                ).addCallback(object : Callback() {
                    override fun onCreate(db: SupportSQLiteDatabase) {
                        super.onCreate(db)
                        // Seed database with approved pilot baseline
                        CoroutineScope(Dispatchers.IO).launch {
                            val dao = getInstance(context).farmDao()
                            dao.insertOrUpdateProfile(FarmProfileEntity())
                            dao.insertOrUpdateAdvice(AdviceEntity())
                            dao.insertHistoryItem(AdviceHistoryEntity())
                        }
                    }
                }).build()
                INSTANCE = instance
                instance
            }
        }
    }
}
