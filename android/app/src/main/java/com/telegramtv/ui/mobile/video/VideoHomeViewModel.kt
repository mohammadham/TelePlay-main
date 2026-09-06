package com.telegramtv.ui.mobile.video
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.telegramtv.data.repository.VideoRepository
import com.telegramtv.data.model.VideoBrowse
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class VideoHomeViewModel @Inject constructor(private val repo: VideoRepository) : ViewModel() {
    private val _browse = MutableStateFlow<VideoBrowse?>(null)
    val browse: StateFlow<VideoBrowse?> = _browse
    fun load() { viewModelScope.launch { repo.getBrowse().onSuccess { _browse.value = it } } }
}
