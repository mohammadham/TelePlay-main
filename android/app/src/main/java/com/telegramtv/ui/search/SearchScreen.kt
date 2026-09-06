package com.telegramtv.ui.search

import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.*
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.tv.foundation.lazy.grid.TvGridCells
import androidx.tv.foundation.lazy.grid.TvLazyVerticalGrid
import androidx.tv.foundation.lazy.grid.items
import androidx.tv.material3.Card
import androidx.tv.material3.CardDefaults
import coil.compose.AsyncImage
import com.telegramtv.data.model.Track
import com.telegramtv.ui.components.*
import com.telegramtv.ui.theme.*

/**
 * Search screen for finding files and music.
 */

@Composable
fun SearchScreen(
    onFileClick: (Int) -> Unit,
    onTrackClick: (Int) -> Unit = {},
    onBackClick: () -> Unit,
    viewModel: SearchViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()
    val searchFieldFocus = remember { FocusRequester() }
    var selectedMode by remember { mutableStateOf(SearchMode.FILES) }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(TVBackground)
    ) {
        Column(modifier = Modifier.fillMaxSize()) {
            // Search header
            SearchHeader(
                query = uiState.query,
                onQueryChange = { viewModel.onQueryChange(it) },
                onClear = { viewModel.clearSearch() },
                onBack = onBackClick,
                focusRequester = searchFieldFocus
            )

            // Mode tabs
            TabRow(
                selectedTabIndex = if (selectedMode == SearchMode.MUSIC) 1 else 0,
                containerColor = TVBackground,
                contentColor = TVTextPrimary,
                modifier = Modifier.padding(horizontal = 48.dp)
            ) {
                Tab(
                    selected = selectedMode == SearchMode.FILES,
                    onClick = { selectedMode = SearchMode.FILES },
                    text = { Text("Files", color = if (selectedMode == SearchMode.FILES) TVTextPrimary else TVTextSecondary) }
                )
                Tab(
                    selected = selectedMode == SearchMode.MUSIC,
                    onClick = { selectedMode = SearchMode.MUSIC },
                    text = { Text("Music", color = if (selectedMode == SearchMode.MUSIC) TVTextPrimary else TVTextSecondary) }
                )
            }

            // Search results
            when {
                uiState.isSearching -> {
                    LoadingIndicator(
                        message = if (selectedMode == SearchMode.MUSIC) "Searching music..." else "Searching...",
                        modifier = Modifier.weight(1f)
                    )
                }

                uiState.error != null -> {
                    ErrorState(
                        message = uiState.error!!,
                        onRetry = { viewModel.onQueryChange(uiState.query) },
                        modifier = Modifier.weight(1f)
                    )
                }

                selectedMode == SearchMode.MUSIC && uiState.musicResults.isNotEmpty() -> {
                    // Music results grid
                    TvLazyVerticalGrid(
                        columns = TvGridCells.Adaptive(200.dp),
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(horizontal = 48.dp, vertical = 16.dp),
                        contentPadding = PaddingValues(horizontal = 48.dp, vertical = 16.dp),
                        horizontalArrangement = Arrangement.spacedBy(16.dp),
                        verticalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        items(uiState.musicResults, key = { it.id }) { track ->
                            MusicResultCard(
                                track = track,
                                onClick = { onTrackClick(track.fileId) }
                            )
                        }
                    }
                }

                selectedMode == SearchMode.FILES && uiState.results.isNotEmpty() -> {
                    // Results count
                    Text(
                        text = "${uiState.results.size} results",
                        style = MaterialTheme.typography.bodyMedium,
                        color = TVTextSecondary,
                        modifier = Modifier.padding(horizontal = 48.dp, vertical = 8.dp)
                    )

                    // Results grid
                    TvLazyVerticalGrid(
                        columns = TvGridCells.Adaptive(200.dp),
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(horizontal = 48.dp, vertical = 8.dp),
                        contentPadding = PaddingValues(horizontal = 48.dp, vertical = 16.dp),
                        horizontalArrangement = Arrangement.spacedBy(16.dp),
                        verticalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        items(uiState.results, key = { it.id }) { file ->
                            val thumbnailUrl = "${uiState.serverUrl}/api/stream/${file.id}/thumbnail"
                            MediaCard(
                                file = file,
                                thumbnailUrl = thumbnailUrl,
                                onClick = { onFileClick(file.id) }
                            )
                        }
                    }
                }

                uiState.hasSearched && (
                    (selectedMode == SearchMode.FILES && uiState.results.isEmpty()) ||
                    (selectedMode == SearchMode.MUSIC && uiState.musicResults.isEmpty())
                ) -> {
                    EmptyState(
                        title = "No results found",
                        subtitle = "Try a different search term",
                        modifier = Modifier.weight(1f)
                    )
                }

                else -> {
                    // Initial state - no search yet
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .fillMaxWidth(),
                        contentAlignment = Alignment.Center
                    ) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Icon(
                                imageVector = Icons.Default.Search,
                                contentDescription = null,
                                modifier = Modifier.size(64.dp),
                                tint = TVTextSecondary
                            )
                            Spacer(modifier = Modifier.height(16.dp))
                            Text(
                                text = "Search your files and music",
                                style = MaterialTheme.typography.titleMedium,
                                color = TVTextSecondary
                            )
                        }
                    }
                }
            }
        }
    }

    // Focus search field on launch
    LaunchedEffect(Unit) {
        searchFieldFocus.requestFocus()
    }
}

/**
 * Search header with input field.
 */
@Composable
private fun SearchHeader(
    query: String,
    onQueryChange: (String) -> Unit,
    onClear: () -> Unit,
    onBack: () -> Unit,
    focusRequester: FocusRequester
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 48.dp, vertical = 24.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        // Back button
        TVIconButton(
            icon = {
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                    contentDescription = "Back",
                    tint = TVTextPrimary,
                    modifier = Modifier.size(24.dp)
                )
            },
            onClick = onBack,
            modifier = Modifier.size(48.dp)
        )

        Spacer(modifier = Modifier.width(24.dp))

        // Search input
        Box(
            modifier = Modifier
                .weight(1f)
                .height(56.dp)
                .background(TVSurfaceVariant, MaterialTheme.shapes.medium)
                .padding(horizontal = 16.dp),
            contentAlignment = Alignment.CenterStart
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(
                    imageVector = Icons.Default.Search,
                    contentDescription = null,
                    tint = TVTextSecondary,
                    modifier = Modifier.size(24.dp)
                )

                Spacer(modifier = Modifier.width(12.dp))

                BasicTextField(
                    value = query,
                    onValueChange = onQueryChange,
                    modifier = Modifier
                        .weight(1f)
                        .focusRequester(focusRequester),
                    textStyle = MaterialTheme.typography.bodyLarge.copy(
                        color = TVTextPrimary
                    ),
                    singleLine = true,
                    cursorBrush = SolidColor(TVPrimary),
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
                    keyboardActions = KeyboardActions(
                        onSearch = { /* Already searching with debounce */ }
                    ),
                    decorationBox = { innerTextField ->
                        if (query.isEmpty()) {
                            Text(
                                text = "Search files and music...",
                                style = MaterialTheme.typography.bodyLarge,
                                color = TVTextSecondary
                            )
                        }
                        innerTextField()
                    }
                )

                if (query.isNotEmpty()) {
                    IconButton(onClick = onClear) {
                        Icon(
                            imageVector = Icons.Default.Clear,
                            contentDescription = "Clear",
                            tint = TVTextSecondary
                        )
                    }
                }
            }
        }
    }
}

/**
 * Music result card for TV search.
 */
@OptIn(ExperimentalTvMaterial3Api::class)
@Composable
private fun MusicResultCard(
    track: Track,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    var isFocused by remember { mutableStateOf(false) }
    val scale by animateFloatAsState(
        targetValue = if (isFocused) 1.05f else 1f,
        animationSpec = spring(dampingRatio = Spring.DampingRatioMediumBouncy, stiffness = Spring.StiffnessMedium),
        label = "musicResultCardScale"
    )

    Card(
        onClick = onClick,
        modifier = modifier
            .width(180.dp)
            .height(240.dp)
            .scale(scale)
            .onFocusChanged { isFocused = it.isFocused }
            .then(if (isFocused) Modifier.shadow(elevation = 12.dp, shape = RoundedCornerShape(12.dp), ambientColor = TVAccentGlow) else Modifier),
        colors = CardDefaults.colors(containerColor = if (isFocused) TVCardFocused else TVCardBackground),
        shape = CardDefaults.shape(shape = RoundedCornerShape(12.dp))
    ) {
        Box(modifier = Modifier.fillMaxSize()) {
            // Cover image
            if (!track.coverUrl.isNullOrBlank()) {
                AsyncImage(
                    model = track.coverUrl,
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
                    .background(Brush.verticalGradient(listOf(Color.Transparent, Color.Black.copy(alpha = 0.9f))))
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
