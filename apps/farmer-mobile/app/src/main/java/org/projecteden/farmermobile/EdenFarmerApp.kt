package org.projecteden.farmermobile

import android.app.Application
import org.projecteden.farmermobile.audio.BanglaTtsManager
import org.projecteden.farmermobile.data.local.EdenDatabase
import org.projecteden.farmermobile.data.repository.FarmerRepository

class EdenFarmerApp : Application() {

    lateinit var database: EdenDatabase
        private set

    lateinit var repository: FarmerRepository
        private set

    lateinit var ttsManager: BanglaTtsManager
        private set

    override fun onCreate() {
        super.onCreate()
        database = EdenDatabase.getInstance(this)
        repository = FarmerRepository(database.farmDao())
        ttsManager = BanglaTtsManager(this)
    }

    override fun onTerminate() {
        super.onTerminate()
        ttsManager.shutdown()
    }
}
