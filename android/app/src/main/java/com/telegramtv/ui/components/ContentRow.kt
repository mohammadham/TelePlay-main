package com.telegramtv.ui.components

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.Spring
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.MusicNote
import androidx.compose.material.icons.filled.VideoLibrary
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.tv.foundation.lazy.list.TvLazyRow
import androidx.tv.foundation.lazy.list.items
import androidx.tv.material3.Card
import androidx.tv.material3.CardDefaults
import androidx.tv.material3.ExperimentalTvMaterial3Api
import coil.compose.AsyncImage
import com.telegramtv.data.model.FileItem
import com.telegramtv.data.model.Folder
import com.telegramtv.data.model.TVMusicTrack
import com.telegramtv.ui.theme.*

private fun buildImageUrl(path: String?, serverUrl: String): String? {
    if (path.isNullOrBlank()) return null
    return if (path.startsWith("http")) path else "$serverUrl$path"
}

/**
 * Horizontal content row for the home screen.
 * Displays a title and horizontally scrolling items.
 */
@Composable
fun ContentRow(
    title: String,
    files: List<FileItem>,
    serverUrl: String,
    onFileClick: (Int) -> Unit,
    modifier: Modifier = Modifier,
    useLargeCards: Boolean = false
) {
    Column(modifier = modifier) {
        // Row title
        Text(
            text = title,
            style = MaterialTheme.typography.headlineSmall,
            color = TVTextPrimary,
            modifier = Modifier.padding(start = 48.dp, bottom = 16.dp)
        )

        // Horizontal scrollable items
        TvLazyRow(
            contentPadding = PaddingValues(horizontal = 48.dp),
            horizontalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            items(files, key = { it.id }) { file ->
                val thumbnailUrl = "$serverUrl/api/stream/${file.id}/thumbnail"

                if (useLargeCards) {
                    LargeMediaCard(
                        file = file,
                        thumbnailUrl = thumbnailUrl,
                        onClick = { onFileClick(file.id) }
                    )
                } else {
                    MediaCard(
                        file = file,
                        thumbnailUrl = thumbnailUrl,
                        onClick = { onFileClick(file.id) }
                    )
                }
            }
        }
    }
}

/**
 * Horizontal music track row for the home screen.
 */
@Composable
fun MusicRow(
    title: String,
    tracks: List<TVMusicTrack>,
    serverUrl: String,
    onTrackClick: (Int) -> Unit,
    modifier: Modifier = Modifier,
    showBadge: Boolean = true
) {
    Column(modifier = modifier) {
        Text(
            text = title,
            style = MaterialTheme.typography.headlineSmall,
            color = TVTextPrimary,
            modifier = Modifier.padding(start = 48.dp, bottom = 16.dp)
        )

        TvLazyRow(
            contentPadding = PaddingValues(horizontal = 48.dp),
            horizontalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            items(tracks, key = { it.id }) { track ->
                MusicCard(
                    track = track,
                    serverUrl = serverUrl,
                    streamUrl = serverUrl + (track.streamUrl ?: ""),
                    onClick = { onTrackClick(track.fileId) }
                )
            }
        }
    }
}

/**
 * Music card for TV home screen.
 */
@OptIn(ExperimentalTvMaterial3Api::class)
@Composable
private fun MusicCard(
    track: TVMusicTrack,
    serverUrl: String,
    streamUrl: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    var isFocused by remember { mutableStateOf(false) }
    val scale by animateFloatAsState(
        targetValue = if (isFocused) 1.08f else 1f,
        animationSpec = spring(
            dampingRatio = Spring.DampingRatioMediumBouncy,
            stiffness = Spring.StiffnessMedium
        ),
        label = "musicCardScale"
    )

    Card(
        onClick = onClick,
        modifier = modifier
            .width(160.dp)
            .height(220.dp)
            .scale(scale)
            .onFocusChanged { isFocused = it.isFocused }
            .then(
                if (isFocused) Modifier.shadow(
                    elevation = 12.dp,
                    shape = RoundedCornerShape(12.dp),
                    ambientColor = TVAccentGlow
                ) else Modifier
            ),
        colors = CardDefaults.colors(
            containerColor = if (isFocused) TVCardFocused else TVCardBackground
        ),
        shape = CardDefaults.shape(shape = RoundedCornerShape(12.dp))
    ) {
        Box(modifier = Modifier.fillMaxSize()) {
            // Cover image
            val coverUrl = buildImageUrl(track.coverUrl, serverUrl)
            if (!coverUrl.isNullOrBlank()) {
                AsyncImage(
                    model = coverUrl,
                    contentDescription = track.title,
                    modifier = Modifier.fillMaxSize(),
                    contentScale = ContentScale.Crop
                )
            } else {
                Box(
                    modifier = Modifier.fillMaxSize().background(Color(0xFF1A1A2E)),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        Icons.Default.MusicNote,
                        contentDescription = null,
                        tint = TVPrimary.copy(alpha = 0.5f),
                        modifier = Modifier.size(48.dp)
                    )
                }
            }

            // Gradient overlay
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(80.dp)
                    .align(Alignment.BottomCenter)
                    .background(
                        Brush.verticalGradient(
                            colors = listOf(Color.Transparent, Color.Black.copy(alpha = 0.9f))
                        )
                    )
            )

            // Media type badge
            if (track.mediaType != "audio") {
                Box(
                    modifier = Modifier
                        .align(Alignment.TopEnd)
                        .padding(8.dp)
                        .background(
                            color = if (track.mediaType == "reel") Color(0xFF8B5CF6) else Color(0xFFEF4444),
                            shape = RoundedCornerShape(4.dp)
                        )
                        .padding(horizontal = 6.dp, vertical = 2.dp)
                ) {
                    Text(
                        text = if (track.mediaType == "reel") "Reel" else "MV",
                        style = MaterialTheme.typography.labelSmall,
                        color = Color.White
                    )
                }
            }

            // Track info
            Column(
                modifier = Modifier
                    .align(Alignment.BottomStart)
                    .padding(12.dp)
            ) {
                Text(
                    text = track.title,
                    style = MaterialTheme.typography.bodyMedium,
                    color = TVTextPrimary,
                    fontWeight = if (isFocused) FontWeight.SemiBold else FontWeight.Normal,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = track.artist?.name ?: "Unknown",
                    style = MaterialTheme.typography.labelSmall,
                    color = TVTextSecondary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            }
        }
    }
}

/**
 * Horizontal folder row for the home screen.
 */
@Composable
fun FolderRow(
    title: String,
    folders: List<Folder>,
    onFolderClick: (Int) -> Unit,
    modifier: Modifier = Modifier
) {
    Column(modifier = modifier) {
        // Row title
        Text(
            text = title,
            style = MaterialTheme.typography.headlineSmall,
            color = TVTextPrimary,
            modifier = Modifier.padding(start = 48.dp, bottom = 16.dp)
        )

        // Horizontal scrollable folders
        TvLazyRow(
            contentPadding = PaddingValues(horizontal = 48.dp),
            horizontalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            items(folders, key = { it.id }) { folder ->
                FolderCard(
                    folder = folder,
                    onClick = { onFolderClick(folder.id) }
                )
            }
        }
    }
}
