package org.projecteden.farmermobile.ui.screens.today

import android.app.Application
import android.util.Log
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import kotlinx.coroutines.CancellationException
import org.projecteden.farmermobile.EdenFarmerApp
import org.projecteden.farmermobile.audio.AudioPlaybackState
import org.projecteden.farmermobile.data.model.AdviceEntity

class TodayAdviceViewModel(application: Application) : AndroidViewModel(application) {

    private val app = application as EdenFarmerApp
    private val repository = app.repository
    private val ttsManager = app.ttsManager

    val advice: StateFlow<AdviceEntity> = repository.currentAdvice.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5000),
        initialValue = AdviceEntity()
    )

    val playbackState: StateFlow<AudioPlaybackState> = ttsManager.playbackState

    private val _isRefreshing = MutableStateFlow(false)
    val isRefreshing: StateFlow<Boolean> = _isRefreshing.asStateFlow()

    private val _refreshMessage = MutableStateFlow<String?>(null)
    val refreshMessage: StateFlow<String?> = _refreshMessage.asStateFlow()

    init {
        // Sync with the server when the Today screen opens; the cached advice stays if it is unreachable.
        refreshAdvice()
    }

    fun playAudio() {
        Log.i(TAG, "advice_audio_started")
        ttsManager.playAdvice(advice.value.audioScriptBangla, advice.value.audioDurationSeconds)
    }

    fun pauseOrStopAudio() {
        Log.i(TAG, "advice_audio_stopped")
        ttsManager.pauseOrStop()
    }

    fun refreshAdvice() {
        if (_isRefreshing.value) return
        viewModelScope.launch {
            _isRefreshing.value = true
            _refreshMessage.value = null
            Log.i(TAG, "advice_refresh_started")
            try {
                repository.refreshAdvice().fold(
                    onSuccess = {
                        _refreshMessage.value = "সর্বশেষ পরামর্শ হালনাগাদ হয়েছে"
                        Log.i(TAG, "advice_refresh_succeeded")
                    },
                    onFailure = { error ->
                        _refreshMessage.value = "সার্ভারে সংযোগ হয়নি; সংরক্ষিত পরামর্শ দেখানো হচ্ছে"
                        Log.w(TAG, "advice_refresh_failed:${error.javaClass.simpleName}")
                    }
                )
            } catch (error: CancellationException) {
                throw error
            } catch (error: Exception) {
                _refreshMessage.value = "সার্ভারে সংযোগ হয়নি; সংরক্ষিত পরামর্শ দেখানো হচ্ছে"
                Log.w(TAG, "advice_refresh_failed:${error.javaClass.simpleName}")
            } finally {
                _isRefreshing.value = false
            }
        }
    }

    private companion object {
        const val TAG = "EDEN_APP"
    }
}
