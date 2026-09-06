package com.telegramtv.data.model

import com.google.gson.annotations.SerializedName

/**
 * TV-specific API responses optimized for home screen.
 */

/**
 * TV Browse response - returns all data needed for home screen in one call.
 */
data class TVBrowseResponse(
    @SerializedName("continue_watching") val continueWatching: List<FileItem>,
    @SerializedName("recent") val recentFiles: List<FileItem>,
    @SerializedName("folders") val folders: List<Folder>,
    @SerializedName("featured_music_videos") val featuredMusicVideos: List<TVMusicTrack> = emptyList(),
    @SerializedName("music_history_by_genre") val musicHistoryByGenre: Map<String, List<TVMusicTrack>> = emptyMap()
)

/**
 * Search result response.
 */
data class SearchResponse(
    @SerializedName("query") val query: String,
    @SerializedName("results") val results: List<FileItem>,
    @SerializedName("total") val total: Int,
    @SerializedName("music") val musicResults: List<TVMusicTrack> = emptyList()
)

/**
 * TV-optimized music track (simplified from Track model).
 */
data class TVMusicTrack(
    val id: Int,
    val title: String,
    @SerializedName("artist_id") val artistId: Int? = null,
    val artist: TVArtist? = null,
    @SerializedName("file_id") val fileId: Int,
    val duration: Int? = null,
    val genre: String? = null,
    @SerializedName("play_count") val playCount: Int = 0,
    @SerializedName("like_count") val likeCount: Int = 0,
    @SerializedName("stream_url") val streamUrl: String? = null,
    @SerializedName("cover_url") val coverUrl: String? = null,
    @SerializedName("media_type") val mediaType: String = "audio"
)

/**
 * Simplified TV artist model.
 */
data class TVArtist(
    val id: Int,
    val name: String
)
