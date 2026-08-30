package com.telegramtv.data.repository

import com.telegramtv.data.api.TelePlayApi
import com.telegramtv.data.model.*
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class VideoRepository @Inject constructor(private val api: TelePlayApi) {
    suspend fun getBrowse(): Result<VideoBrowse> = try {
        val r = api.getVideoBrowse()
        if (r.isSuccessful) Result.success(r.body()!!) else Result.failure(Exception("browse ${r.code()}"))
    } catch (e: Exception) { Result.failure(e) }

    suspend fun getMovies(genre: String? = null, q: String? = null): Result<List<Movie>> = try {
        val r = api.getMovies(genre, q)
        if (r.isSuccessful) Result.success(r.body()!!) else Result.failure(Exception(r.message()))
    } catch (e: Exception) { Result.failure(e) }

    suspend fun updateProgress(fileId: Int, position: Int) = try {
        api.updateVideoProgress(mapOf("file_id" to fileId, "position" to position))
        Result.success(Unit)
    } catch (e: Exception) { Result.failure(e) }
}
