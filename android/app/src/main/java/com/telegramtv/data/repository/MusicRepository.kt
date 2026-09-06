package com.telegramtv.data.repository

import com.telegramtv.data.api.TelePlayApi
import com.telegramtv.data.model.*
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class MusicRepository @Inject constructor(private val api: TelePlayApi) {
    suspend fun getTracks(q: String? = null, artistId: Int? = null, mediaType: String? = null): Result<List<Track>> = try {
        val r = api.getTracks(q, artistId, mediaType)
        if (r.isSuccessful) Result.success(r.body()!!) else Result.failure(Exception("tracks ${r.code()}"))
    } catch (e: Exception) { Result.failure(e) }

    suspend fun getArtists(q: String? = null): Result<List<Artist>> = try {
        val r = api.getArtists(q)
        if (r.isSuccessful) Result.success(r.body()!!) else Result.failure(Exception(r.message()))
    } catch (e: Exception) { Result.failure(e) }

    suspend fun getAlbums(artistId: Int? = null): Result<List<Album>> = try {
        val r = api.getAlbums(artistId)
        if (r.isSuccessful) Result.success(r.body()!!) else Result.failure(Exception(r.message()))
    } catch (e: Exception) { Result.failure(e) }

    suspend fun getPlaylists(): Result<List<Playlist>> = try {
        val r = api.getPlaylists()
        if (r.isSuccessful) Result.success(r.body()!!) else Result.failure(Exception(r.message()))
    } catch (e: Exception) { Result.failure(e) }

    suspend fun likeTrack(id: Int): Result<Unit> = try {
        val r = api.likeTrack(id)
        if (r.isSuccessful) Result.success(Unit) else Result.failure(Exception(r.message()))
    } catch (e: Exception) { Result.failure(e) }

    suspend fun addDownload(trackId: Int): Result<Unit> = try {
        val r = api.addDownload(mapOf("track_id" to trackId))
        if (r.isSuccessful) Result.success(Unit) else Result.failure(Exception(r.message()))
    } catch (e: Exception) { Result.failure(e) }

    suspend fun getDownloads(): Result<List<DownloadItem>> = try {
        val r = api.getDownloads()
        if (r.isSuccessful) Result.success(r.body()!!) else Result.failure(Exception(r.message()))
    } catch (e: Exception) { Result.failure(e) }

    // TV-specific methods
    suspend fun getFeaturedMusicVideos(): Result<List<com.telegramtv.data.model.TVMusicTrack>> = try {
        val r = api.getMusicFeatured()
        if (r.isSuccessful) Result.success(r.body()!!) else Result.failure(Exception("featured ${r.code()}"))
    } catch (e: Exception) { Result.failure(e) }

    suspend fun getMusicHistoryByGenre(limit: Int = 20): Result<Map<String, List<com.telegramtv.data.model.TVMusicTrack>>> = try {
        val r = api.getMusicHistoryByGenre(limit)
        if (r.isSuccessful) Result.success(r.body()!!) else Result.failure(Exception("genre ${r.code()}"))
    } catch (e: Exception) { Result.failure(e) }
}
