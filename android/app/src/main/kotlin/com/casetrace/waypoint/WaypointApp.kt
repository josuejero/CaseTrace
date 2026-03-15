package com.casetrace.waypoint

import android.app.Application
import androidx.room.Room
import com.casetrace.waypoint.data.local.CoreDatabase
import com.casetrace.waypoint.data.local.WebDatabase
import com.casetrace.waypoint.data.repository.WaypointRepository
import com.casetrace.waypoint.domain.SeedUseCase

class AppContainer(application: Application) {
    private val context = application.applicationContext

    val coreDatabase: CoreDatabase by lazy {
        Room.databaseBuilder(context, CoreDatabase::class.java, "waypoint_core.db")
            .setJournalMode(CoreDatabase.JournalMode.WRITE_AHEAD_LOGGING)
            .build()
    }

    val webDatabase: WebDatabase by lazy {
        Room.databaseBuilder(context, WebDatabase::class.java, "waypoint_web.db")
            .setJournalMode(WebDatabase.JournalMode.WRITE_AHEAD_LOGGING)
            .build()
    }

    val repository by lazy { WaypointRepository(coreDatabase, webDatabase) }
    val seedUseCase by lazy { SeedUseCase(coreDatabase, webDatabase, context) }
}

class WaypointApp : Application() {
    val container by lazy { AppContainer(this) }
}
