package com.casetrace.waypoint.data.local

import androidx.room.*
import kotlinx.coroutines.flow.Flow
import java.time.Instant

@Entity(tableName = "browser_history")
data class BrowserVisitEntity(
    @PrimaryKey val id: Long,
    val title: String,
    val url: String,
    val typedUrl: Boolean,
    val referrer: String?,
    val timestamp: Instant
)

@Dao
interface BrowserVisitDao {
    @Query("SELECT * FROM browser_history ORDER BY timestamp")
    fun observeAll(): Flow<List<BrowserVisitEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(vararg entries: BrowserVisitEntity)

    @Query("DELETE FROM browser_history")
    suspend fun deleteAll()

    @Query("DELETE FROM browser_history WHERE id = :id")
    suspend fun deleteById(id: Long)
}

@Database(entities = [BrowserVisitEntity::class], version = 1, exportSchema = true)
@TypeConverters(Converters::class)
abstract class WebDatabase : RoomDatabase() {
    abstract fun browserVisitDao(): BrowserVisitDao
}
