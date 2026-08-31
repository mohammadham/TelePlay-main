package com.telegramtv.data.model

import com.google.gson.annotations.SerializedName

data class Artist(
    val id: Int,
    val name: String,
    val bio: String? = null,
    val verified: Boolean = false,
    @SerializedName("created_at") val createdAt: String
)

data class Album(
    val id: Int,
    val title: String,
    @SerializedName("artist_id") val artistId: Int,
    val artist: Artist? = null,
    val genre: String? = null,
    @SerializedName("total_tracks") val totalTracks: Int = 0
)

data class Track(
    val id: Int,
    val title: String,
    @SerializedName("artist_id") val artistId: Int,
    val artist: Artist? = null,
    @SerializedName("album_id") val albumId: Int? = null,
    val album: Album? = null,
    @SerializedName("file_id") val fileId: Int,
    val duration: Int? = null,
    val genre: String? = null,
    @SerializedName("play_count") val playCount: Int = 0,
    @SerializedName("like_count") val likeCount: Int = 0,
    @SerializedName("stream_url") val streamUrl: String? = null,
    @SerializedName("cover_url") val coverUrl: String? = null,
    @SerializedName("is_liked") val isLiked: Boolean = false
)

data class Playlist(
    val id: Int,
    @SerializedName("user_id") val userId: Int,
    val title: String,
    @SerializedName("is_public") val isPublic: Boolean = false,
    val tracks: List<Track> = emptyList(),
    @SerializedName("created_at") val createdAt: String
)

data class DownloadItem(
    val id: Int,
    val status: String,
    val progress: Int,
    val track: Track?,
    @SerializedName("created_at") val createdAt: String
)
