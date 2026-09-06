package com.telegramtv.ui.mobile.video
import android.content.Context
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import coil.compose.rememberAsyncImagePainter
import coil.request.ImageRequest
import com.telegramtv.data.model.Movie

@Composable
fun MobileVideoHomeScreen(onPlayMovie: (Int) -> Unit, vm: VideoHomeViewModel = hiltViewModel()) {
    val browse by vm.browse.collectAsState()
    LaunchedEffect(Unit) { vm.load() }
    LazyColumn(modifier = Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        browse?.hero?.let { hero ->
            item {
                Card(modifier = Modifier.fillMaxWidth().height(200.dp)) {
                    Image(
                        painter = rememberAsyncImagePainter(
                            ImageRequest.Builder(LocalContext.current)
                                .data(hero.thumbnailUrl ?: "")
                                .build()
                        ),
                        contentDescription = hero.title,
                        modifier = Modifier.fillMaxSize(),
                        contentScale = ContentScale.Crop
                    )
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text(hero.title, style = MaterialTheme.typography.titleLarge, color = Color.White)
                        Text(hero.genre ?: "", style = MaterialTheme.typography.bodySmall, color = Color.White.copy(alpha = 0.7f))
                        Button(onClick = { onPlayMovie(hero.fileId) }, modifier = Modifier.padding(top = 8.dp)) { Text("Play") }
                    }
                }
            }
        }
        browse?.continueWatching?.takeIf { it.isNotEmpty() }?.let { items ->
            item { Text("Continue Watching", style = MaterialTheme.typography.titleMedium) }
            item {
                LazyRow(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    items(items) { m ->
                        Column(modifier = Modifier.width(140.dp)) {
                            Card(modifier = Modifier.width(140.dp).height(200.dp)) {
                                if (!m.thumbnailUrl.isNullOrEmpty()) {
                                    Image(
                                        painter = rememberAsyncImagePainter(
                                            ImageRequest.Builder(LocalContext.current)
                                                .data(m.thumbnailUrl)
                                                .build()
                                        ),
                                        contentDescription = m.title,
                                        modifier = Modifier.fillMaxSize(),
                                        contentScale = ContentScale.Crop
                                    )
                                }
                            }
                            Text(m.title, maxLines = 1, style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            }
        }
        browse?.byGenre?.forEach { (genre, movies) ->
            if (movies.isNotEmpty()) {
                item { Text(genre, style = MaterialTheme.typography.titleMedium) }
                item {
                    LazyRow(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        items(movies) { m ->
                            Column(modifier = Modifier.width(140.dp)) {
                                Card(modifier = Modifier.width(140.dp).height(200.dp)) {
                                    if (!m.thumbnailUrl.isNullOrEmpty()) {
                                        Image(
                                            painter = rememberAsyncImagePainter(
                                                ImageRequest.Builder(LocalContext.current)
                                                    .data(m.thumbnailUrl)
                                                    .build()
                                            ),
                                            contentDescription = m.title,
                                            modifier = Modifier.fillMaxSize(),
                                            contentScale = ContentScale.Crop
                                        )
                                    }
                                }
                                Text(m.title, maxLines = 1, style = MaterialTheme.typography.bodySmall)
                            }
                        }
                    }
                }
            }
        }
    }
}
