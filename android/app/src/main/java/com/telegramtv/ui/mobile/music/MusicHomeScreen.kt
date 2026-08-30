package com.telegramtv.ui.mobile.music

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.telegramtv.ui.components.MediaCard
import androidx.compose.foundation.clickable

@Composable
fun MusicHomeScreen(onPlayTrack: (Int) -> Unit, vm: MusicViewModel = hiltViewModel()) {
    val tracks by vm.tracks.collectAsState()
    val artists by vm.artists.collectAsState()
    LaunchedEffect(Unit) { vm.load() }
    LazyColumn(modifier = Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        item { Text("Recently Added", style = MaterialTheme.typography.titleLarge) }
        item {
            LazyRow(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                items(tracks) { t ->
                    // reuse MediaCard for track (cover + title)
                    Column(modifier = Modifier.width(140.dp).clickable { onPlayTrack(t.fileId) }) {
                        // fallback: simple card
                        Card { Column(modifier = Modifier.padding(8.dp)) {
                            Text(t.title, maxLines = 1, style = MaterialTheme.typography.bodyMedium)
                            Text(t.artist?.name ?: "Unknown", style = MaterialTheme.typography.bodySmall)
                        } }
                    }
                }
            }
        }
        item { Text("Popular Artists", style = MaterialTheme.typography.titleMedium) }
        item {
            LazyRow(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                items(artists) { a ->
                    Card(modifier = Modifier.width(100.dp)) { Column(modifier = Modifier.padding(8.dp)) {
                        Text(a.name, maxLines = 1)
                    } }
                }
            }
        }
        item { Text("Ad • banner placeholder (یک‌تانت)", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant) }
    }
}
