package com.telegramtv.data.model

import com.google.gson.annotations.SerializedName

data class Movie(
    val id: Int,
    val title: String,
    val description: String? = null,
    val genre: String? = null,
    val year: Int? = null,
    @SerializedName("file_id") val fileId: Int,
    val duration: Int? = null,
    val featured: Boolean = false,
    @SerializedName("stream_url") val streamUrl: String? = null,
    @SerializedName("thumbnail_url") val thumbnailUrl: String? = null
)

data class Series(
    val id: Int,
    val title: String,
    val description: String? = null,
    val genre: String? = null,
    val year: Int? = null
)

data class Episode(
    val id: Int,
    @SerializedName("series_id") val seriesId: Int,
    val season: Int,
    val episode: Int,
    val title: String,
    @SerializedName("file_id") val fileId: Int
)

data class VideoBrowse(
    val hero: Movie?,
    @SerializedName("continue_watching") val continueWatching: List<Movie> = emptyList(),
    @SerializedName("by_genre") val byGenre: Map<String, List<Movie>> = emptyMap()
)
