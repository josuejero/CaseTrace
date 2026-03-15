package com.casetrace.waypoint.domain

import com.casetrace.waypoint.domain.seed.SeedProfiles
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class SeedProfileTest {
    private val profile = SeedProfiles.caseAlpha

    @Test
    fun `case alpha message commit matches count`() {
        assertEquals(8, profile.messages.size)
        assertEquals(4, profile.calls.size)
        assertEquals(6, profile.browsers.size)
        assertEquals(10, profile.locations.size)
        assertEquals(4, profile.photos.size)
        assertEquals(8, profile.events.size)
    }

    @Test
    fun `recovered summary references Harbor Cafe and alley`() {
        assertTrue(profile.deletedMessage.body.contains("Harbor Cafe"))
        assertTrue(profile.deletedBrowserVisit.url.contains("maps.example/alleys"))
    }
}
