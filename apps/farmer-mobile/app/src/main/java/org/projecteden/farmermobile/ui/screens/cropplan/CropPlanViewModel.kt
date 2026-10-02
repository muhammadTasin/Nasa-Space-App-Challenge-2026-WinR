package org.projecteden.farmermobile.ui.screens.cropplan

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import org.projecteden.farmermobile.EdenFarmerApp
import org.projecteden.farmermobile.data.model.AdviceEntity

class CropPlanViewModel(application: Application) : AndroidViewModel(application) {

    private val repository = (application as EdenFarmerApp).repository

    val advice: StateFlow<AdviceEntity> = repository.currentAdvice.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5000),
        initialValue = AdviceEntity()
    )
}
