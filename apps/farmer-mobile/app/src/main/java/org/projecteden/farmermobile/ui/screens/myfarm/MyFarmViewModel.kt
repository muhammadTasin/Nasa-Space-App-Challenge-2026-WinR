package org.projecteden.farmermobile.ui.screens.myfarm

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
import org.projecteden.farmermobile.data.model.FarmProfileEntity

class MyFarmViewModel(application: Application) : AndroidViewModel(application) {

    private val repository = (application as EdenFarmerApp).repository

    val farmProfile: StateFlow<FarmProfileEntity> = repository.farmProfile.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5000),
        initialValue = FarmProfileEntity()
    )

    private val _isUpdating = MutableStateFlow(false)
    val isUpdating: StateFlow<Boolean> = _isUpdating.asStateFlow()

    private val _feedbackMessage = MutableStateFlow<String?>(null)
    val feedbackMessage: StateFlow<String?> = _feedbackMessage.asStateFlow()

    fun updateFarmInfo() {
        viewModelScope.launch {
            _isUpdating.value = true
            delay(800) // Brief feedback
            repository.saveProfile(farmProfile.value)
            _feedbackMessage.value = "খামারের তথ্য সফলভাবে হালনাগাদ ও ক্যাশ করা হয়েছে"
            _isUpdating.value = false
            delay(2500)
            _feedbackMessage.value = null
        }
    }
}
