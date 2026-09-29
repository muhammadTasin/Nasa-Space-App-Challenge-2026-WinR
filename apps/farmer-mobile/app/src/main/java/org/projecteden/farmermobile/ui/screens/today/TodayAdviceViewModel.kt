package org.projecteden.farmermobile.ui.screens.today

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
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

    init {
        // Sync with the server when the Today screen opens; the cached advice stays if it is unreachable.
        refreshAdvice()
    }

    fun playAudio() {
        ttsManager.playAdvice(advice.value.audioScriptBangla, advice.value.audioDurationSeconds)
    }

    fun pauseOrStopAudio() {
        ttsManager.pauseOrStop()
    }

    fun refreshAdvice() {
        viewModelScope.launch {
            _isRefreshing.value = true
            repository.refreshAdvice()
            _isRefreshing.value = false
        }
    }
}
