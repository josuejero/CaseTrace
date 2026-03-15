package com.casetrace.waypoint.data.local

import androidx.room.*
import kotlinx.coroutines.flow.Flow
import java.time.Instant

@Entity(tableName = "messages")
data class MessageEntity(
    @PrimaryKey val id: Long,
    val threadId: String,
    val direction: MessageDirection,
    val timestamp: Instant,
    val sender: String,
    val recipient: String,
    val body: String,
    val readFlag: Boolean,
    val deletedFlag: Boolean
)

@Entity(tableName = "calls")
data class CallEntity(
    @PrimaryKey val id: Long,
    val callType: CallType,
    val contactName: String,
    val timestampStart: Instant,
    val timestampEnd: Instant,
    val durationSeconds: Int,
    val summary: String
)

@Entity(tableName = "photos")
data class PhotoEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val fileName: String,
    val timestamp: Instant,
    val summary: String,
    val latitude: Double,
    val longitude: Double,
    val deviceModel: String,
    val orientation: Int
)

@Entity(tableName = "app_events")
data class AppEventEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val eventType: String,
    val timestampStart: Instant,
    val timestampEnd: Instant,
    val summary: String
)

enum class MessageDirection {
    INBOUND,
    OUTBOUND
}

enum class CallType {
    PLACED,
    RECEIVED,
    MISSED
}

object Converters {
    @TypeConverter
    @JvmStatic
    fun toInstant(value: Long?): Instant? = value?.let { Instant.ofEpochMilli(it) }

    @TypeConverter
    @JvmStatic
    fun fromInstant(value: Instant?): Long? = value?.toEpochMilli()

    @TypeConverter
    @JvmStatic
    fun fromDirection(direction: MessageDirection?): String? = direction?.name

    @TypeConverter
    @JvmStatic
    fun toDirection(value: String?): MessageDirection? = value?.let { MessageDirection.valueOf(it) }

    @TypeConverter
    @JvmStatic
    fun fromCallType(callType: CallType?): String? = callType?.name

    @TypeConverter
    @JvmStatic
    fun toCallType(value: String?): CallType? = value?.let { CallType.valueOf(it) }
}

@Dao
interface MessageDao {
    @Query("SELECT * FROM messages ORDER BY timestamp")
    fun observeAll(): Flow<List<MessageEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(vararg rows: MessageEntity)

    @Query("DELETE FROM messages")
    suspend fun deleteAll()

    @Query("DELETE FROM messages WHERE id = :id")
    suspend fun deleteById(id: Long)

    @Update
    suspend fun update(message: MessageEntity)
}

@Dao
interface CallDao {
    @Query("SELECT * FROM calls ORDER BY timestampStart")
    fun observeAll(): Flow<List<CallEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(vararg rows: CallEntity)

    @Query("DELETE FROM calls")
    suspend fun deleteAll()
}

@Dao
interface PhotoDao {
    @Query("SELECT * FROM photos ORDER BY timestamp")
    fun observeAll(): Flow<List<PhotoEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(photo: PhotoEntity)

    @Query("DELETE FROM photos")
    suspend fun deleteAll()
}

@Dao
interface AppEventDao {
    @Query("SELECT * FROM app_events ORDER BY timestampStart")
    fun observeAll(): Flow<List<AppEventEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(vararg rows: AppEventEntity)

    @Query("DELETE FROM app_events")
    suspend fun deleteAll()
}

@Database(
    entities = [MessageEntity::class, CallEntity::class, PhotoEntity::class, AppEventEntity::class],
    version = 1,
    exportSchema = true
)
@TypeConverters(Converters::class)
abstract class CoreDatabase : RoomDatabase() {
    abstract fun messageDao(): MessageDao
    abstract fun callDao(): CallDao
    abstract fun photoDao(): PhotoDao
    abstract fun appEventDao(): AppEventDao
}
