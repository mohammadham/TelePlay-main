package com.telegramtv.ui.mobile.music

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import coil.compose.AsyncImage
import coil.request.ImageRequest
import com.telegramtv.data.model.Track

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MusicHomeScreen(onPlayTrack: (Int) -> Unit, vm: MusicViewModel = hiltViewModel()) {
    val tracks by vm.tracks.collectAsState()
    val artists by vm.artists.collectAsState()
    var selectedTab by remember { mutableStateOf(MusicTab.ALL) }

    LaunchedEffect(Unit) { vm.load(selectedTab) }

    // Filter tracks by selected tab
    val filteredTracks = remember(tracks, selectedTab) {
        when (selectedTab) {
            MusicTab.MUSIC_VIDEO -> tracks.filter { it.mediaType == "music_video" }
            MusicTab.REEL -> tracks.filter { it.mediaType == "reel" }
            else -> tracks
        }
    }

    Column(modifier = Modifier.fillMaxSize().background(Color(0xFF121212))) {
        // Tab row
        TabRow(
            selectedTabIndex = selectedTab.ordinal,
            containerColor = Color(0xFF121212),
            contentColor = Color.White
        ) {
            MusicTab.entries.forEach { tab ->
                Tab(
                    selected = selectedTab == tab,
                    onClick = {
                        selectedTab = tab
                        vm.load(tab)
                    },
                    text = {
                        Text(
                            text = tab.label,
                            color = if (selectedTab == tab) MaterialTheme.colorScheme.primary else Color.White.copy(alpha = 0.7f),
                            fontWeight = if (selectedTab == tab) FontWeight.Bold else FontWeight.Normal
                        )
                    }
                )
            }
        }

        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Recently Added / Music Videos / Reels
            item {
                Text(
                    text = when (selectedTab) {
                        MusicTab.MUSIC_VIDEO -> "Music Videos"
                        MusicTab.REEL -> "Reels"
                        else -> "Recently Added"
                    },
                    style = MaterialTheme.typography.titleLarge,
                    color = Color.White
                )
            }
            item {
                LazyRow(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    items(filteredTracks) { track ->
                        TrackCard(track = track, onPlay = { onPlayTrack(track.fileId) })
                    }
                }
            }

            // Popular Artists (shown on ALL tab)
            if (selectedTab == MusicTab.ALL) {
                item {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "Popular Artists",
                        style = MaterialTheme.typography.titleMedium,
                        color = Color.White
                    )
                }
                item {
                    LazyRow(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        items(artists) { artist ->
                            ArtistCard(artist = artist)
                        }
                    }
                }
            }

            item {
                Spacer(modifier = Modifier.height(16.dp))
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    color = Color.Black.copy(alpha = 0.3f),
                    shape = MaterialTheme.shapes.small
                ) {
                    Text(
                        text = "Ad · یک تانت / AdMob",
                        modifier = Modifier.padding(12.dp),
                        style = MaterialTheme.typography.bodySmall,
                        color = Color.White.copy(alpha = 0.5f)
                    )
                }
            }
        }
    }
}

enum class MusicTab(val label: String) {
    ALL("All"),
    MUSIC_VIDEO("Music Videos"),
    REEL("Reels")
}

@Composable
fun TrackCard(track: Track, onPlay: () -> Unit) {
    Column(
        modifier = Modifier
            .width(140.dp)
            .clickable(onClick = onPlay)
    ) {
        Card(
            modifier = Modifier.width(140.dp).height(200.dp),
            shape = MaterialTheme.shapes.medium
        ) {
            if (!track.coverUrl.isNullOrBlank()) {
                AsyncImage(
                    model = ImageRequest.Builder(LocalContext.current)
                        .data(track.coverUrl)
                        .crossfade(true)
                        .build(),
                    contentDescription = track.title,
                    modifier = Modifier.fillMaxSize(),
                    contentScale = androidx.compose.ui.layout.ContentScale.Crop
                )
            } else {
                Box(
                    modifier = Modifier.fillMaxSize().background(Color(0xFF282828)),
                    contentAlignment = Alignment.Center
                ) {
                    Text(text = if (track.mediaType == "reel") "🎬" else "🎵", fontSize = androidx.compose.ui.text.style.TextStyle.Default.fontSize * 2)
                }
            }
            // Media type badge
            if (track.mediaType != "audio") {
                Box(
                    modifier = Modifier
                        .align(Alignment.TopEnd)
                        .padding(4.dp)
                        .background(
                            color = if (track.mediaType == "reel") Color(0xFF8B5CF6) else Color(0xFFEF4444),
                            shape = MaterialTheme.shapes.small
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
        }
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            text = track.title,
            maxLines = 1,
            style = MaterialTheme.typography.bodyMedium,
            color = Color.White
        )
        Text(
            text = track.artist?.name ?: "Unknown",
            maxLines = 1,
            style = MaterialTheme.typography.bodySmall,
            color = Color.White.copy(alpha = 0.6f)
        )
    }
}

@Composable
fun ArtistCard(artist: com.telegramtv.data.model.Artist) {
    Column(
        modifier = Modifier.width(100.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Surface(
            modifier = Modifier.size(80.dp),
            shape = MaterialTheme.shapes.large,
            color = Color(0xFF282828)
        ) {
            Box(contentAlignment = Alignment.Center) {
                Text(text = "🎤", fontSize = androidx.compose.ui.text.style.TextStyle.Default.fontSize * 2.5)
            }
        }
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            text = artist.name,
            maxLines = 2,
            style = MaterialTheme.typography.bodySmall,
            color = Color.White
        )
    }
}
