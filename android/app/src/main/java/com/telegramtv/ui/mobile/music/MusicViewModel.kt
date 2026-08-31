package com.telegramtv.ui.mobile.music

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.telegramtv.data.model.*
import com.telegramtv.data.repository.MusicRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class MusicViewModel @Inject constructor(private val repo: MusicRepository) : ViewModel() {
    private val _tracks = MutableStateFlow<List<Track>>(emptyList())
    val tracks: StateFlow<List<Track>> = _tracks
    private val _artists = MutableStateFlow<List<Artist>>(emptyList())
    val artists: StateFlow<List<Artist>> = _artists
    private val _playlists = MutableStateFlow<List<Playlist>>(emptyList())
    val playlists: StateFlow<List<Playlist>> = _playlists

    fun load() = viewModelScope.launch {
        repo.getTracks().onSuccess { _tracks.value = it }
        repo.getArtists().onSuccess { _artists.value = it }
        repo.getPlaylists().onSuccess { _playlists.value = it }
    }
    fun like(id: Int) = viewModelScope.launch { repo.likeTrack(id) }
    fun download(id: Int) = viewModelScope.launch { repo.addDownload(id) }
}
