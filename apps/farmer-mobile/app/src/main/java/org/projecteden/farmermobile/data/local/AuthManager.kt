package org.projecteden.farmermobile.data.local

import android.content.Context
import android.content.SharedPreferences
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import org.projecteden.farmermobile.data.remote.EdenApiClient
import org.projecteden.farmermobile.data.remote.RemoteAuthResponse

data class AuthUser(
    val userId: String,
    val role: String, // "farmer" or "officer"
    val nameBangla: String,
    val nameEnglish: String,
    val titleBangla: String,
    val blockOrVillage: String,
    val token: String,
    val landType: String? = null,
    val currentAmanCrop: String? = null
)

sealed class AuthState {
    object Guest : AuthState()
    data class Authenticated(val user: AuthUser) : AuthState()
}

class AuthManager(
    private val context: Context,
    private val apiClient: EdenApiClient
) {
    private val prefs: SharedPreferences = context.getSharedPreferences("eden_auth_prefs", Context.MODE_PRIVATE)

    private val _authState = MutableStateFlow<AuthState>(loadSession())
    val authState: StateFlow<AuthState> = _authState.asStateFlow()

    val currentUser: AuthUser?
        get() = (_authState.value as? AuthState.Authenticated)?.user

    val token: String?
        get() = currentUser?.token

    private fun loadSession(): AuthState {
        val token = prefs.getString(KEY_TOKEN, null) ?: return AuthState.Guest
        val userId = prefs.getString(KEY_USER_ID, null) ?: return AuthState.Guest
        val role = prefs.getString(KEY_ROLE, "farmer") ?: "farmer"
        val nameBangla = prefs.getString(KEY_NAME_BN, "কৃষক") ?: "কৃষক"
        val nameEnglish = prefs.getString(KEY_NAME_EN, "Farmer") ?: "Farmer"
        val titleBangla = prefs.getString(KEY_TITLE_BN, "নিবন্ধিত কৃষক") ?: "নিবন্ধিত কৃষক"
        val blockOrVillage = prefs.getString(KEY_BLOCK_VILLAGE, "") ?: ""
        val landType = prefs.getString(KEY_LAND_TYPE, null)
        val currentAmanCrop = prefs.getString(KEY_AMAN_CROP, null)

        return AuthState.Authenticated(
            AuthUser(
                userId = userId,
                role = role,
                nameBangla = nameBangla,
                nameEnglish = nameEnglish,
                titleBangla = titleBangla,
                blockOrVillage = blockOrVillage,
                token = token,
                landType = landType,
                currentAmanCrop = currentAmanCrop
            )
        )
    }

    suspend fun login(role: String, id: String, codeOrPin: String): Result<AuthUser> {
        val res = apiClient.login(role, id, codeOrPin)
        return res.mapCatching { remote ->
            val user = AuthUser(
                userId = remote.userId,
                role = remote.role,
                nameBangla = remote.nameBangla,
                nameEnglish = remote.nameEnglish,
                titleBangla = remote.titleBangla,
                blockOrVillage = remote.blockOrVillage,
                token = remote.token,
                landType = remote.landType,
                currentAmanCrop = remote.currentAmanCrop
            )
            saveSession(user)
            _authState.value = AuthState.Authenticated(user)
            user
        }
    }

    suspend fun logout(): Boolean {
        val currentToken = token
        if (currentToken != null) {
            try {
                apiClient.logout(currentToken)
            } catch (_: Exception) {
                // Ignore network error on logout
            }
        }
        clearSession()
        _authState.value = AuthState.Guest
        return true
    }

    private fun saveSession(user: AuthUser) {
        prefs.edit()
            .putString(KEY_TOKEN, user.token)
            .putString(KEY_USER_ID, user.userId)
            .putString(KEY_ROLE, user.role)
            .putString(KEY_NAME_BN, user.nameBangla)
            .putString(KEY_NAME_EN, user.nameEnglish)
            .putString(KEY_TITLE_BN, user.titleBangla)
            .putString(KEY_BLOCK_VILLAGE, user.blockOrVillage)
            .putString(KEY_LAND_TYPE, user.landType)
            .putString(KEY_AMAN_CROP, user.currentAmanCrop)
            .apply()
    }

    private fun clearSession() {
        prefs.edit().clear().apply()
    }

    companion object {
        private const val KEY_TOKEN = "auth_token"
        private const val KEY_USER_ID = "user_id"
        private const val KEY_ROLE = "user_role"
        private const val KEY_NAME_BN = "name_bn"
        private const val KEY_NAME_EN = "name_en"
        private const val KEY_TITLE_BN = "title_bn"
        private const val KEY_BLOCK_VILLAGE = "block_village"
        private const val KEY_LAND_TYPE = "land_type"
        private const val KEY_AMAN_CROP = "aman_crop"
    }
}
