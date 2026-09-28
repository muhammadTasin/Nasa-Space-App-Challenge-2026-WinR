package org.projecteden.farmermobile.ui.screens.rotationdetail

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import org.projecteden.farmermobile.EdenFarmerApp
import org.projecteden.farmermobile.audio.AudioPlaybackState
import org.projecteden.farmermobile.data.model.AdviceEntity

class RotationDetailViewModel(application: Application) : AndroidViewModel(application) {

    private val app = application as EdenFarmerApp
    private val repository = app.repository
    private val ttsManager = app.ttsManager

    val advice: StateFlow<AdviceEntity> = repository.currentAdvice.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5000),
        initialValue = AdviceEntity()
    )

    val playbackState: StateFlow<AudioPlaybackState> = ttsManager.playbackState

    private val _isConfirmed = MutableStateFlow(false)
    val isConfirmed: StateFlow<Boolean> = _isConfirmed.asStateFlow()

    private val _confirmToast = MutableStateFlow<String?>(null)
    val confirmToast: StateFlow<String?> = _confirmToast.asStateFlow()

    fun playAudio() {
        ttsManager.playAdvice(advice.value.audioScriptBangla, advice.value.audioDurationSeconds)
    }

    fun pauseOrStopAudio() {
        ttsManager.pauseOrStop()
    }

    fun confirmPlan() {
        viewModelScope.launch {
            _isConfirmed.value = true
            _confirmToast.value = "এই ফসল চক্রটি আপনার খামারের পরিকল্পনায় সফলভাবে নিশ্চিত করা হয়েছে"
            delay(3000)
            _confirmToast.value = null
        }
    }
}
