package org.projecteden.farmermobile.ui.screens.erosion

import android.app.Application
import android.util.Log
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import org.projecteden.farmermobile.EdenFarmerApp
import org.projecteden.farmermobile.data.remote.RemoteRiverErosionResponse

sealed class RiverErosionUiState {
    object Loading : RiverErosionUiState()
    data class Success(val data: RemoteRiverErosionResponse) : RiverErosionUiState()
    data class Error(val message: String) : RiverErosionUiState()
}

class RiverErosionViewModel(application: Application) : AndroidViewModel(application) {

    private val app = application as EdenFarmerApp
    private val apiClient = app.apiClient

    private val _uiState = MutableStateFlow<RiverErosionUiState>(RiverErosionUiState.Loading)
    val uiState: StateFlow<RiverErosionUiState> = _uiState.asStateFlow()

    private val _selectedRiver = MutableStateFlow("jamuna")
    val selectedRiver: StateFlow<String> = _selectedRiver.asStateFlow()

    init {
        Log.i(TAG, "erosion_screen_opened")
        loadRiverData("jamuna")
    }

    fun selectRiver(riverId: String) {
        if (_selectedRiver.value == riverId) return
        _selectedRiver.value = riverId
        Log.i(TAG, "erosion_river_selected:$riverId")
        loadRiverData(riverId)
    }

    fun loadRiverData(riverId: String) {
        viewModelScope.launch {
            _uiState.value = RiverErosionUiState.Loading
            val res = apiClient.fetchRiverErosion(riverId)
            res.fold(
                onSuccess = { erosion ->
                    _uiState.value = RiverErosionUiState.Success(erosion)
                    Log.i(TAG, "erosion_load_success:$riverId")
                },
                onFailure = { err ->
                    Log.w(TAG, "erosion_load_failed:${err.message}")
                    _uiState.value = RiverErosionUiState.Error("নদীভাঙন উপাত্ত লোড করা যায়নি; নেটওয়ার্ক চেক করুন।")
                }
            )
        }
    }

    private companion object {
        const val TAG = "EDEN_APP"
    }
}
