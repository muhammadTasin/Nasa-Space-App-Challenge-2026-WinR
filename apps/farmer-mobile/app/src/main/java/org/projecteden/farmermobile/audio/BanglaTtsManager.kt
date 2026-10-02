package org.projecteden.farmermobile.audio

import android.content.Context
import android.os.Handler
import android.os.Looper
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.util.Locale

sealed class AudioPlaybackState {
    data object Idle : AudioPlaybackState()
    data class Playing(val progressFraction: Float, val currentSeconds: Int, val totalSeconds: Int) : AudioPlaybackState()
    data object Paused : AudioPlaybackState()
    data class Error(val messageBangla: String) : AudioPlaybackState()
}

class BanglaTtsManager(context: Context) : TextToSpeech.OnInitListener {

    private var tts: TextToSpeech? = TextToSpeech(context.applicationContext, this)
    private var isInitialized = false
    private var isBanglaSupported = false

    private val _playbackState = MutableStateFlow<AudioPlaybackState>(AudioPlaybackState.Idle)
    val playbackState: StateFlow<AudioPlaybackState> = _playbackState.asStateFlow()

    private val mainHandler = Handler(Looper.getMainLooper())
    private var progressRunnable: Runnable? = null
    private var currentSeconds = 0
    private var estimatedDurationSeconds = 80

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            isInitialized = true
            val bdLocale = Locale.Builder().setLanguage("bn").setRegion("BD").build()
            val generalBn = Locale.Builder().setLanguage("bn").build()

            val bdResult = tts?.isLanguageAvailable(bdLocale) ?: TextToSpeech.LANG_NOT_SUPPORTED
            val isSupported = when (bdResult) {
                TextToSpeech.LANG_AVAILABLE,
                TextToSpeech.LANG_COUNTRY_AVAILABLE,
                TextToSpeech.LANG_COUNTRY_VAR_AVAILABLE -> {
                    tts?.language = bdLocale
                    true
                }
                else -> {
                    val genResult = tts?.isLanguageAvailable(generalBn) ?: TextToSpeech.LANG_NOT_SUPPORTED
                    if (genResult >= TextToSpeech.LANG_AVAILABLE) {
                        tts?.language = generalBn
                        true
                    } else false
                }
            }

            isBanglaSupported = isSupported

            tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                override fun onStart(utteranceId: String?) {
                    currentSeconds = 0
                    startProgressTracker()
                }

                override fun onDone(utteranceId: String?) {
                    stopProgressTracker()
                    mainHandler.post {
                        _playbackState.value = AudioPlaybackState.Idle
                    }
                }

                @Deprecated("Deprecated in Java")
                override fun onError(utteranceId: String?) {
                    stopProgressTracker()
                    mainHandler.post {
                        _playbackState.value = AudioPlaybackState.Error("অডিও প্লেব্যাকে সমস্যা হয়েছে")
                    }
                }
            })
        } else {
            isInitialized = false
            isBanglaSupported = false
        }
    }

    fun playAdvice(textBangla: String, durationEstimate: Int = 80) {
        estimatedDurationSeconds = durationEstimate

        if (!isInitialized) {
            _playbackState.value = AudioPlaybackState.Error("ভয়েস ইঞ্জিন প্রস্তুত হচ্ছে...")
            return
        }

        if (!isBanglaSupported) {
            // Honest notification: do not fake playback
            _playbackState.value = AudioPlaybackState.Error("আপনার ডিভাইসে বাংলা ভয়েস ডাটা পাওয়া যায়নি")
            return
        }

        val utteranceId = "eden_advice_${System.currentTimeMillis()}"
        val result = tts?.speak(textBangla, TextToSpeech.QUEUE_FLUSH, null, utteranceId)
        if (result != TextToSpeech.SUCCESS) {
            _playbackState.value = AudioPlaybackState.Error("অডিও চালু করা যায়নি")
        }
    }

    fun pauseOrStop() {
        stopProgressTracker()
        tts?.stop()
        _playbackState.value = AudioPlaybackState.Idle
    }

    private fun startProgressTracker() {
        stopProgressTracker()
        progressRunnable = object : Runnable {
            override fun run() {
                currentSeconds++
                val fraction = (currentSeconds.toFloat() / estimatedDurationSeconds).coerceIn(0f, 1f)
                _playbackState.value = AudioPlaybackState.Playing(
                    progressFraction = fraction,
                    currentSeconds = currentSeconds,
                    totalSeconds = estimatedDurationSeconds
                )
                if (currentSeconds < estimatedDurationSeconds) {
                    mainHandler.postDelayed(this, 1000)
                }
            }
        }
        mainHandler.post(progressRunnable!!)
    }

    private fun stopProgressTracker() {
        progressRunnable?.let { mainHandler.removeCallbacks(it) }
        progressRunnable = null
    }

    fun shutdown() {
        stopProgressTracker()
        tts?.stop()
        tts?.shutdown()
        tts = null
    }
}
