package org.projecteden.farmermobile

import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.projecteden.farmermobile.data.local.FarmDao
import org.projecteden.farmermobile.data.model.AdviceEntity
import org.projecteden.farmermobile.data.model.AdviceHistoryEntity
import org.projecteden.farmermobile.data.model.FarmProfileEntity
import org.projecteden.farmermobile.data.repository.FarmerRepository
import org.projecteden.farmermobile.ui.components.formatBanglaTimer
import org.projecteden.farmermobile.ui.components.toBanglaDigits

class FarmerMobileUnitTest {

    @Test
    fun testBanglaDigitConversion() {
        assertEquals("০", 0.toBanglaDigits())
        assertEquals("১", 1.toBanglaDigits())
        assertEquals("১০", 10.toBanglaDigits())
        assertEquals("২৫", 25.toBanglaDigits())
        assertEquals("২০২৬", 2026.toBanglaDigits())
    }

    @Test
    fun testBanglaTimerFormatting() {
        val timer = formatBanglaTimer(currentSec = 8, totalSec = 80)
        assertEquals("০:০৮ / ১:২০", timer)
    }

    @Test
    fun testFarmProfileDefaults() {
        val profile = FarmProfileEntity()
        assertEquals("তালান্দা পাইলট খামার", profile.farmName)
        assertEquals("মাঝারি উঁচু জমি", profile.landType)
        assertEquals("বেলে-দোআঁশ মাটি", profile.soilTexture)
        assertTrue(profile.priorities.contains("পানি সাশ্রয়ী সেচ"))
    }

    @Test
    fun testAdviceHonestMissingValues() {
        val advice = AdviceEntity()
        assertEquals("তথ্য পাওয়া যায়নি", advice.season1IrrigationStatus)
        assertEquals("তথ্য পাওয়া যায়নি", advice.season2FertilizerRecommendation)
        assertEquals("তথ্য পাওয়া যায়নি", advice.alternativeCropMarketPrice)
        assertEquals("আমন ধান ➔ সরিষা", advice.rotationTitle)
    }

    @Test
    fun testRepositoryFallbackWhenDaoEmpty() = runTest {
        val fakeDao = object : FarmDao {
            override fun getFarmProfile() = flowOf(null)
            override suspend fun insertOrUpdateProfile(profile: FarmProfileEntity) {}
            override fun getAdvice() = flowOf(null)
            override suspend fun insertOrUpdateAdvice(advice: AdviceEntity) {}
            override fun getAdviceHistory() = flowOf(emptyList<AdviceHistoryEntity>())
            override suspend fun insertHistoryItem(item: AdviceHistoryEntity) {}
        }

        val repository = FarmerRepository(fakeDao)

        val profile = repository.farmProfile.first()
        assertNotNull(profile)
        assertEquals("তালান্দা পাইলট খামার", profile.farmName)

        val advice = repository.currentAdvice.first()
        assertNotNull(advice)
        assertEquals("আমন ধান ➔ সরিষা", advice.rotationTitle)

        val history = repository.adviceHistory.first()
        assertEquals(1, history.size)
        assertEquals("আমন ধান (ব্রি ধান-৪৯) ➔ সরিষা", history[0].rotationTitle)
    }
}
