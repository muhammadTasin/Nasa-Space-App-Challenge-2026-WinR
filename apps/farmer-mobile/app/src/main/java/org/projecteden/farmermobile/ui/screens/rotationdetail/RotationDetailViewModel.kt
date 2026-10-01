package org.projecteden.farmermobile.ui.screens.rotationdetail

import android.app.Application
import android.content.Context
import android.util.Log
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.launch
import org.projecteden.farmermobile.EdenFarmerApp
import org.projecteden.farmermobile.audio.AudioPlaybackState
import org.projecteden.farmermobile.data.model.AdviceEntity

class RotationDetailViewModel(application: Application) : AndroidViewModel(application) {

    private val app = application as EdenFarmerApp
    private val repository = app.repository
    private val ttsManager = app.ttsManager
    private val preferences = app.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)

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

    init {
        viewModelScope.launch {
            repository.currentAdvice.collect { current ->
                _isConfirmed.value = preferences.getString(CONFIRMED_PLAN_KEY, null) == confirmationKey(current)
            }
        }
    }

    fun playAudio() {
        Log.i(TAG, "rotation_audio_started")
        ttsManager.playAdvice(advice.value.audioScriptBangla, advice.value.audioDurationSeconds)
    }

    fun pauseOrStopAudio() {
        Log.i(TAG, "rotation_audio_stopped")
        ttsManager.pauseOrStop()
    }

    fun confirmPlan() {
        viewModelScope.launch {
            if (_isConfirmed.value) {
                _confirmToast.value = "এই পরিকল্পনাটি আগেই নিশ্চিত করা হয়েছে"
                delay(2500)
                _confirmToast.value = null
                return@launch
            }

            val current = advice.value
            try {
                repository.recordPlanConfirmation(current)
                preferences.edit().putString(CONFIRMED_PLAN_KEY, confirmationKey(current)).apply()
                _isConfirmed.value = true
                _confirmToast.value = "পরিকল্পনাটি এই ডিভাইসে সংরক্ষণ করা হয়েছে"
                Log.i(TAG, "plan_confirmed")
                delay(3000)
                _confirmToast.value = null
            } catch (error: CancellationException) {
                throw error
            } catch (error: Exception) {
                _confirmToast.value = "পরিকল্পনাটি সংরক্ষণ করা যায়নি; আবার চেষ্টা করুন"
                Log.w(TAG, "plan_confirmation_failed:${error.javaClass.simpleName}")
                delay(3000)
                _confirmToast.value = null
            }
        }
    }

    private fun confirmationKey(current: AdviceEntity): String =
        "${current.updatedAt}|${current.rotationTitle}|${current.season2Variety}"

    private companion object {
        const val TAG = "EDEN_APP"
        const val PREFERENCES_NAME = "eden_farmer"
        const val CONFIRMED_PLAN_KEY = "confirmed_plan_key"
    }
}
