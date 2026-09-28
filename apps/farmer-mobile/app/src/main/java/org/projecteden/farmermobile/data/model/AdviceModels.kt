package org.projecteden.farmermobile.data.model

import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * Cached seasonal advice entity matching the Stitch cleaned screens.
 * Contains honest missing data labels ("তথ্য পাওয়া যায়নি") for unmeasured parameters.
 */
@Entity(tableName = "cached_advice")
data class AdviceEntity(
    @PrimaryKey
    val id: String = "current_seasonal_advice",
    val plotName: String = "পূর্ব মাঠ – প্লট ০২ (তালান্দা এলাকা)",
    val blockTag: String = "আমন ব্লক",
    val guidelineApproval: String = "অনুমোদিত কৃষি গাইডলাইন অনুযায়ী",
    val cacheTimeString: String = "সকাল ৭:০০ ক্যাশে",
    val rotationTitle: String = "আমন ধান ➔ সরিষা",
    val rotationSubtitle: String = "ব্রি ধান-৪৯ থেকে স্বল্প মেয়াদী বারি সরিষা-১৪ রোটেশন",
    // Season 1
    val season1Name: String = "আমন ধান",
    val season1Variety: String = "ব্রি ধান-৪৯",
    val season1Window: String = "রোপণ: জুলাই – আগস্ট • কর্তন: নভেম্বর – ডিসেম্বর",
    val season1Stage: String = "মাঠ পর্যায়: কুশি গজানোর মধ্যবর্তী ধাপ",
    val season1SoilStatus: String = "উপযোগী / জো অবস্থা",
    val season1IrrigationStatus: String = "তথ্য পাওয়া যায়নি",
    // Season 2
    val season2Name: String = "সরিষা",
    val season2Variety: String = "বারি সরিষা-১৪",
    val season2Window: String = "বপন: নভেম্বর শেষ – ডিসেম্বর ১ম সপ্তাহ • সংগ্রহ: ফেব্রুয়ারি",
    val season2Notes: String = "মাটির গুণমান বৃদ্ধি ও দ্রুত ফলনের উপযোগী",
    val season2FertilizerRecommendation: String = "তথ্য পাওয়া যায়নি",
    // Narrative Advisory
    val narrativeAdvice: String = "মাটির আর্দ্রতা ধরে রাখা ও রবি মৌসুমে জমি ফেলে না রেখে স্বল্প মেয়াদী সরিষা চাষের জন্য কৃষি সম্প্রসারণ অধিদপ্তর (DAE) কর্তৃক অনুমোদিত ফসল ক্রম।",
    // Alternative crop
    val alternativeCropName: String = "গম (বারি গম-৩৩)",
    val alternativeCropCategory: String = "মাঝারি সেচ",
    val alternativeCropSowing: String = "নভেম্বর – ডিসেম্বর",
    val alternativeCropYield: String = "উচ্চ ফলনশীল",
    val alternativeCropMarketPrice: String = "তথ্য পাওয়া যায়নি",
    // Provenance
    val provenanceNotice: String = "তথ্যসূত্র: অনুমোদিত কৃষি গাইডলাইন ও স্থানীয় সম্প্রসারণ সেবা। অসম্পূর্ণ তথ্য যাচাইয়ের জন্য স্থানীয় উপসহকারী কৃষি কর্মকর্তার সাথে যোগাযোগ করুন।",
    // Metadata
    val isOffline: Boolean = true,
    val lastSyncFormatted: String = "আজ সকাল ০৮:৩০",
    val audioDurationSeconds: Int = 80,
    val audioScriptBangla: String = "পূর্ব মাঠের প্লট দুই এর জন্য বর্তমান সুপারিশকৃত ফসল ক্রম হলো আমন ধান থেকে সরিষা। ব্রি ধান উনপঞ্চাশ কাটার পর জমি প্রস্তুত করে স্বল্প মেয়াদী বারি সরিষা চৌদ্দ বপন করুন। মাটিতে পর্যাপ্ত রস বজায় রাখুন। বিস্তারিত সহায়তায় স্থানীয় উপসহকারী কৃষি কর্মকর্তার পরামর্শ নিন।",
    val updatedAt: Long = System.currentTimeMillis()
)

/**
 * Historical advice entity for past seasons.
 */
@Entity(tableName = "advice_history")
data class AdviceHistoryEntity(
    @PrimaryKey
    val id: String = "hist_01",
    val seasonTag: String = "সর্বশেষ পরামর্শ • চলতি মৌসুম",
    val rotationTitle: String = "আমন ধান (ব্রি ধান-৪৯) ➔ সরিষা",
    val adviceSummary: String = "ধান কাটার পর সরিষা বপনের জন্য জমি প্রস্তুত রাখুন এবং মাটিতে পরিমিত রস বজায় রাখুন।",
    val hasListenedAudio: Boolean = true,
    val syncTimestamp: String = "আজ সকাল ০৮:৩০",
    val createdAt: Long = System.currentTimeMillis()
)
