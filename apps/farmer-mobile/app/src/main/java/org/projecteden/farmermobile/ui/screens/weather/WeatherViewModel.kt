package org.projecteden.farmermobile.ui.screens.weather

import android.app.Application
import android.util.Log
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import org.projecteden.farmermobile.EdenFarmerApp
import org.projecteden.farmermobile.data.remote.RemoteWeatherResponse

sealed class WeatherUiState {
    object Loading : WeatherUiState()
    data class Success(val data: RemoteWeatherResponse) : WeatherUiState()
    data class Error(val message: String, val cached: RemoteWeatherResponse? = null) : WeatherUiState()
}

class WeatherViewModel(application: Application) : AndroidViewModel(application) {

    private val app = application as EdenFarmerApp
    private val apiClient = app.apiClient

    private val _uiState = MutableStateFlow<WeatherUiState>(WeatherUiState.Loading)
    val uiState: StateFlow<WeatherUiState> = _uiState.asStateFlow()

    private val _isRefreshing = MutableStateFlow(false)
    val isRefreshing: StateFlow<Boolean> = _isRefreshing.asStateFlow()

    init {
        loadWeather()
    }

    fun loadWeather() {
        if (_isRefreshing.value) return
        viewModelScope.launch {
            _isRefreshing.value = true
            Log.i(TAG, "weather_refresh_started")
            val res = apiClient.fetchWeather()
            res.fold(
                onSuccess = { weather ->
                    _uiState.value = WeatherUiState.Success(weather)
                    Log.i(TAG, "weather_refresh_success:live=${weather.isLive}")
                },
                onFailure = { err ->
                    Log.w(TAG, "weather_refresh_failed:${err.javaClass.simpleName}")
                    val currentSuccess = (_uiState.value as? WeatherUiState.Success)?.data
                    _uiState.value = WeatherUiState.Error(
                        message = "আবহাওয়া উপাত্ত হালনাগাদ করা যায়নি; নেটওয়ার্ক চেক করুন।",
                        cached = currentSuccess
                    )
                }
            )
            _isRefreshing.value = false
        }
    }

    private companion object {
        const val TAG = "EDEN_APP"
    }
}
