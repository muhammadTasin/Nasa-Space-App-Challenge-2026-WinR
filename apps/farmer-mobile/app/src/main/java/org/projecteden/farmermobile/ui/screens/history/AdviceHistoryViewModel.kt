package org.projecteden.farmermobile.ui.screens.history

import android.app.Application
import android.util.Log
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import org.projecteden.farmermobile.EdenFarmerApp
import org.projecteden.farmermobile.audio.AudioPlaybackState
import org.projecteden.farmermobile.data.model.AdviceEntity
import org.projecteden.farmermobile.data.model.AdviceHistoryEntity

class AdviceHistoryViewModel(application: Application) : AndroidViewModel(application) {

    private val app = application as EdenFarmerApp
    private val repository = app.repository
    private val ttsManager = app.ttsManager

    val historyList: StateFlow<List<AdviceHistoryEntity>> = repository.adviceHistory.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5000),
        initialValue = listOf(AdviceHistoryEntity())
    )

    val currentAdvice: StateFlow<AdviceEntity> = repository.currentAdvice.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5000),
        initialValue = AdviceEntity()
    )

    val playbackState: StateFlow<AudioPlaybackState> = ttsManager.playbackState

    fun playAudio(item: AdviceHistoryEntity) {
        Log.i(TAG, "history_audio_started")
        ttsManager.playAdvice(item.adviceSummary)
        viewModelScope.launch {
            repository.markAudioListened(item.id)
        }
    }

    fun pauseOrStopAudio() {
        Log.i(TAG, "history_audio_stopped")
        ttsManager.pauseOrStop()
    }

    private companion object {
        const val TAG = "EDEN_APP"
    }
}
