package com.casetrace.waypoint.data.repository

import com.casetrace.waypoint.data.local.*
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class WaypointRepository(
    private val coreDatabase: CoreDatabase,
    private val webDatabase: WebDatabase,
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO
) {
    fun observeMessages() = coreDatabase.messageDao().observeAll()
    fun observeCalls() = coreDatabase.callDao().observeAll()
    fun observePhotos() = coreDatabase.photoDao().observeAll()
    fun observeAppEvents() = coreDatabase.appEventDao().observeAll()
    fun observeBrowserVisits() = webDatabase.browserVisitDao().observeAll()

    suspend fun wipeAllData() = withContext(ioDispatcher) {
        coreDatabase.photoDao().deleteAll()
        coreDatabase.appEventDao().deleteAll()
        coreDatabase.callDao().deleteAll()
        coreDatabase.messageDao().deleteAll()
        webDatabase.browserVisitDao().deleteAll()
    }
}
