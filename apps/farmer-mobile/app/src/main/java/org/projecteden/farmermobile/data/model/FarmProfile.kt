package org.projecteden.farmermobile.data.model

import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * Farm Profile Entity for offline-first persistence in Room.
 * Follows approved pilot specifications for Talanda Union, Tanore, Rajshahi.
 */
@Entity(tableName = "farm_profile")
data class FarmProfileEntity(
    @PrimaryKey
    val id: String = "primary_pilot_farm",
    val farmName: String = "তালান্দা পাইলট খামার",
    val pilotZoneTag: String = "পাইলট জোন",
    val sampleTag: String = "নমুনা পাইলট তথ্য",
    val region: String = "তানোর, রাজশাহী কৃষি এলাকা",
    val geoArea: String = "তালান্দা পাইলট এলাকা, তানোর, রাজশাহী",
    val plotDescription: String = "পাইলট প্রদর্শনী প্লট",
    val totalArea: String = "নমুনা জরিপাধীন",
    val landType: String = "মাঝারি উঁচু জমি",
    val landTypeEnglish: String = "(Medium High)",
    val soilTexture: String = "বেলে-দোআঁশ মাটি",
    val soilTextureEnglish: String = "(Sandy Loam)",
    val irrigationFacility: String = "গভীর নলকূপ ও ভূ-উপরিস্থ ড্রেনেজ সুবিধা সংবলিত",
    val priorities: String = "পানি সাশ্রয়ী সেচ,মুনাফা বৃদ্ধি,মাটির স্বাস্থ্য সংরক্ষণ",
    val consentStatus: String = "সম্মতি দেওয়া আছে",
    val consentValidity: String = "মেয়াদ: ২০২৫",
    val consentDescription: String = "ডিজিটাল কৃষি পরামর্শ সেবা গ্রহণের সম্মতি সক্রিয়",
    val consentDisclaimer: String = "খামারের উপাত্ত কেবল সুনির্দিষ্ট ফসলি পরামর্শ ও আবহাওয়া পূর্বাভাস বিশ্লেষণের কাজে স্বচ্ছতার সাথে ব্যবহৃত হয়।",
    val lastUpdatedFormatted: String = "সকাল ৭:০০",
    val lastUpdatedTimestamp: Long = System.currentTimeMillis()
)
