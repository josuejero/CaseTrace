package com.casetrace.waypoint.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.casetrace.waypoint.data.repository.WaypointRepository
import com.casetrace.waypoint.domain.SeedUseCase
import com.casetrace.waypoint.domain.seed.SeedLocationPoint
import com.casetrace.waypoint.domain.seed.SeedProfiles
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.time.Instant

class MainViewModel(
    repository: WaypointRepository,
    private val seedUseCase: SeedUseCase
) : ViewModel() {
    val messages = repository.observeMessages()
    val calls = repository.observeCalls()
    val photos = repository.observePhotos()
    val appEvents = repository.observeAppEvents()
    val browserVisits = repository.observeBrowserVisits()
    val locationPoints = MutableStateFlow<List<SeedLocationPoint>>(SeedProfiles.caseAlpha.locations)

    private val _seededAt = MutableStateFlow<Instant?>(null)
    val seededAt: StateFlow<Instant?> = _seededAt.asStateFlow()

    private val _mutatedAt = MutableStateFlow<Instant?>(null)
    val mutatedAt: StateFlow<Instant?> = _mutatedAt.asStateFlow()

    private val _snackbar = MutableSharedFlow<String>()
    val snackbar = _snackbar.asSharedFlow()

    init {
        seedDevice()
    }

    fun seedDevice() {
        viewModelScope.launch {
            seedUseCase.seed(SeedProfiles.caseAlpha)
            _seededAt.value = Instant.now()
            _snackbar.emit("Seeded device with ${SeedProfiles.caseAlpha.name}")
        }
    }

    fun mutateAndDelete() {
        viewModelScope.launch {
            seedUseCase.mutateAndDelete(SeedProfiles.caseAlpha)
            _mutatedAt.value = Instant.now()
            _snackbar.emit("Mutate + Delete completed, WAL contains new changes")
        }
    }
}

class MainViewModelFactory(
    private val repository: WaypointRepository,
    private val seedUseCase: SeedUseCase
) : androidx.lifecycle.ViewModelProvider.Factory {
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(MainViewModel::class.java)) {
            @Suppress("UNCHECKED_CAST")
            return MainViewModel(repository, seedUseCase) as T
        }
        throw IllegalArgumentException("Unknown ViewModel class: $modelClass")
    }
}
