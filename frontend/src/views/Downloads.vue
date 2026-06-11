<template>
  <div class="min-h-dvh overflow-x-hidden">
    <Navbar />
    <Settings />

    <div class="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <!-- Header -->
      <div class="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 class="text-2xl font-bold tracking-tight">
            {{ t('library.title') }}
          </h1>
          <p class="mt-1 text-sm text-base-content/60">
            {{ t('library.subtitle') }}
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-2 justify-end">
          <button
            v-if="selectedCount > 0"
            class="btn btn-error btn-sm h-11 px-5 rounded-full btn-outline"
            :disabled="batchDeleting"
            @click="onDeleteSelected"
          >
            <span
              v-if="batchDeleting"
              class="loading loading-spinner loading-xs mr-2"
            />
            {{ t('library.deleteSelected', { count: selectedCount }) }}
          </button>
          <button
            v-if="totalItems > 0"
            class="btn btn-primary btn-sm h-11 px-5 rounded-full"
            @click="playAll"
            :title="t('library.play')"
          >
            <Icon icon="clarity:play-line" class="h-4 w-4 mr-1.5" />
            {{ t('library.play') }}
          </button>
          <button
            class="btn btn-sm h-11 px-5 rounded-full border-white/10 bg-base-100/85 hover:bg-base-100"
            @click="refresh"
            :disabled="loading"
          >
            <span
              v-if="loading"
              class="loading loading-spinner loading-xs mr-2"
            />
            <Icon v-else icon="clarity:refresh-line" class="h-4 w-4 mr-2" />
            {{ t('common.refresh') }}
          </button>
        </div>
      </div>

      <!-- Library search (local only; navbar search is hidden on this page) -->
      <div class="relative mb-6">
        <Icon
          icon="clarity:search-line"
          class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-base-content/40 pointer-events-none"
        />
        <input
          v-model="libraryFilterQuery"
          type="text"
          class="input input-bordered w-full pl-10 pr-10 h-11 rounded-full bg-base-100/85 border-white/10"
          :placeholder="t('library.searchPlaceholder')"
          autocomplete="off"
        />
        <button
          v-if="libraryFilterQuery"
          type="button"
          class="absolute right-2 top-1/2 -translate-y-1/2 icon-btn h-8 w-8"
          :title="t('common.close')"
          @click="clearLibraryFilter"
        >
          <Icon icon="clarity:times-line" class="h-4 w-4" />
        </button>
      </div>

      <p
        v-if="pathsScanning"
        class="mb-3 text-xs text-base-content/50 text-center"
      >
        {{ t('library.pathsScanning') }}
      </p>

      <!-- Playlist filter + bulk selection -->
      <div
        v-if="totalItems > 0"
        class="mb-4 flex flex-wrap items-center gap-2"
      >
        <label class="text-xs text-base-content/50 shrink-0">
          {{ t('library.filterByPlaylist') }}
        </label>
        <PlaylistFilterSelect
          v-model="playlistFilter"
          :options="playlistNames"
          :all-label="t('library.filterAllPlaylists')"
        />
        <button
          v-if="playlistFilter"
          type="button"
          class="btn btn-error btn-sm rounded-full btn-outline"
          :disabled="playlistDeleting"
          @click="onDeletePlaylist"
        >
          <span
            v-if="playlistDeleting"
            class="loading loading-spinner loading-xs mr-2"
          />
          {{ t('library.deletePlaylist') }}
        </button>
        <span class="flex-1" />
        <button
          v-if="paginatedFiles.length > 0"
          type="button"
          class="btn btn-ghost btn-xs rounded-full"
          @click="toggleSelectAllPage"
        >
          {{
            allPageSelected
              ? t('library.clearSelection')
              : t('library.selectAllFiltered')
          }}
        </button>
      </div>

      <!-- Error -->
      <div
        v-if="error"
        class="surface rounded-2xl p-4 mb-4 flex gap-3 items-center text-sm text-error"
      >
        <Icon icon="clarity:exclamation-circle-line" class="h-5 w-5 shrink-0" />
        <span>{{ error }}</span>
      </div>

      <!-- Loading skeleton -->
      <div v-if="loading && files.length === 0" class="space-y-3">
        <div v-for="n in 4" :key="n" class="skeleton h-16 rounded-2xl" />
      </div>

      <!-- No search matches -->
      <div
        v-else-if="
          !loading &&
          totalItems === 0 &&
          (libraryFilterQuery.trim() || playlistFilter)
        "
        class="surface rounded-2xl p-12 flex flex-col items-center text-center"
      >
        <Icon
          icon="clarity:search-line"
          class="h-12 w-12 text-base-content/20 mb-4"
        />
        <p class="text-base-content/50 text-sm">
          {{ t('library.searchNoResults') }}
        </p>
      </div>

      <!-- Empty library -->
      <div
        v-else-if="!loading && totalItems === 0"
        class="surface rounded-2xl p-12 flex flex-col items-center text-center"
      >
        <Icon
          icon="clarity:library-line"
          class="h-12 w-12 text-base-content/20 mb-4"
        />
        <p class="text-base-content/50 text-sm">{{ t('library.empty') }}</p>
        <p class="text-base-content/40 text-xs mt-1">
          {{ t('library.emptyHint') }}
        </p>
      </div>

      <!-- File list -->
      <ul v-else class="space-y-2">
        <li
          v-for="entry in paginatedFiles"
          :key="entry.file"
          class="surface rounded-2xl p-3 sm:p-4 flex items-center gap-3"
        >
          <input
            type="checkbox"
            class="checkbox checkbox-sm checkbox-primary shrink-0"
            :checked="selectedFiles.has(entry.file)"
            @change="toggleSelect(entry.file)"
          />
          <!-- Cover thumb -->
          <div
            class="relative h-11 w-11 shrink-0 rounded-xl bg-primary/10 text-primary flex items-center justify-center overflow-hidden"
          >
            <img
              v-if="entry.has_cover && !coverFailed[entry.file]"
              :src="coverUrlFor(entry.file)"
              :alt="entry.title"
              class="absolute inset-0 h-full w-full object-cover"
              loading="lazy"
              @error="markCoverFailed(entry.file)"
            />
            <Icon v-else icon="clarity:music-note-line" class="h-5 w-5" />
          </div>

          <!-- Title / path -->
          <div class="flex-1 min-w-0">
            <span class="text-sm font-medium truncate block">{{
              entry.title
            }}</span>
            <p
              v-if="entry.artist"
              class="text-xs text-base-content/60 truncate"
            >
              {{ entry.artist }}
            </p>
            <p v-if="entry.album" class="text-xs text-base-content/50 truncate">
              {{ entry.album }}
            </p>
            <div
              v-if="entry.playlists?.length"
              class="flex flex-wrap gap-1 mt-1"
            >
              <span
                v-for="pl in entry.playlists"
                :key="pl"
                class="badge badge-xs border-primary/30 bg-primary/10 text-primary max-w-full truncate"
                :title="pl"
              >
                {{ pl }}
              </span>
            </div>
            <span class="text-xs text-base-content/40">
              <span v-if="folderOf(entry.file)" class="mr-2 text-primary/70">
                <Icon
                  icon="clarity:folder-line"
                  class="inline h-3 w-3 mr-0.5 align-text-top"
                />{{ folderOf(entry.file) }}
              </span>
              {{ formatExt(entry.file) }}
            </span>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-1 shrink-0">
            <button
              class="icon-btn text-primary hover:bg-primary/10"
              @click="playEntry(entry)"
              :title="t('library.play')"
            >
              <Icon icon="clarity:play-line" class="h-4 w-4" />
            </button>
            <a
              class="icon-btn"
              :href="API.downloadFileURL(entry.file)"
              :download="API.downloadSaveName(entry.file)"
              :title="t('library.downloadToDevice')"
            >
              <Icon icon="clarity:download-line" class="h-4 w-4" />
            </a>
            <button
              class="icon-btn text-error/70 hover:text-error hover:bg-error/10"
              :disabled="deleting[entry.file] === true"
              @click="onDelete(entry.file)"
              :title="t('library.deleteFile')"
            >
              <span
                v-if="deleting[entry.file] === true"
                class="loading loading-spinner loading-xs"
              />
              <Icon v-else icon="clarity:trash-line" class="h-4 w-4" />
            </button>
          </div>
        </li>
      </ul>

      <LibraryPagination
        v-if="totalItems > 0"
        :current-page="currentPage"
        :total-pages="totalPages"
        :total-items="totalItems"
        :page-size="pageSize"
        @update:current-page="onPageChange"
        @update:page-size="onPageSizeChange"
      />

      <!-- Count footer -->
      <p
        v-if="totalItems > 0"
        class="mt-4 text-xs text-base-content/40 text-center"
      >
        <template v-if="libraryFilterQuery.trim() || playlistFilter">
          {{
            t('library.filteredCount', {
              shown: paginatedFiles.length,
              total: totalItems,
            })
          }}
        </template>
        <template v-else>
          {{
            totalItems === 1
              ? t('library.countOne', { count: totalItems })
              : t('library.countMany', { count: totalItems })
          }}
        </template>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { Icon } from '@iconify/vue'
import { useRouter } from 'vue-router'
import Navbar from '/src/components/Navbar.vue'
import PlaylistFilterSelect from '/src/components/PlaylistFilterSelect.vue'
import Settings from '/src/components/Settings.vue'
import LibraryPagination from '/src/components/LibraryPagination.vue'
import API from '/src/model/api'
import { useI18n } from '/src/i18n'
import { useLibraryFilter } from '/src/model/libraryFilter'
import {
  normalizeLibraryEntry,
  savePlayerViewPrefs,
  usePlayer,
} from '/src/model/player'

const PAGE_SIZE_STORAGE_KEY = 'downtify.libraryPageSize'
const DEFAULT_PAGE_SIZE = 25

const { t } = useI18n()
const player = usePlayer()
const router = useRouter()
const { libraryFilterQuery, clearLibraryFilter } = useLibraryFilter()

const files = ref([])
const totalItems = ref(0)
const loading = ref(false)
const error = ref('')
const deleting = ref({})
const batchDeleting = ref(false)
const playlistDeleting = ref(false)
const coverFailed = ref({})
const currentPage = ref(1)
const pageSize = ref(readPageSize())
const selectedFiles = ref(new Set())
const playlistFilter = ref('')
const playlistNames = ref([])
const pathsScanning = ref(false)
let filterDebounce = null

const paginatedFiles = computed(() => files.value)

const selectedCount = computed(() => selectedFiles.value.size)

const allPageSelected = computed(() => {
  if (!paginatedFiles.value.length) return false
  return paginatedFiles.value.every((e) => selectedFiles.value.has(e.file))
})

const totalPages = computed(() =>
  Math.max(1, Math.ceil(totalItems.value / pageSize.value))
)

watch([libraryFilterQuery, playlistFilter], () => {
  currentPage.value = 1
  scheduleLoad()
})

watch(pageSize, () => {
  currentPage.value = 1
  loadPage()
})

function toggleSelect(file) {
  const next = new Set(selectedFiles.value)
  if (next.has(file)) next.delete(file)
  else next.add(file)
  selectedFiles.value = next
}

function toggleSelectAllPage() {
  if (allPageSelected.value) {
    selectedFiles.value = new Set()
    return
  }
  selectedFiles.value = new Set(paginatedFiles.value.map((entry) => entry.file))
}

function removeFilesFromList(paths) {
  const gone = new Set(paths)
  files.value = files.value.filter((entry) => !gone.has(entry.file))
  totalItems.value = Math.max(0, totalItems.value - gone.size)
  const next = new Set(selectedFiles.value)
  for (const p of gone) next.delete(p)
  selectedFiles.value = next
}

function readPageSize() {
  try {
    const raw = parseInt(localStorage.getItem(PAGE_SIZE_STORAGE_KEY) || '', 10)
    if ([10, 25, 50, 100].includes(raw)) return raw
  } catch {
    /* ignore */
  }
  return DEFAULT_PAGE_SIZE
}

function onPageSizeChange(size) {
  pageSize.value = size
  currentPage.value = 1
  try {
    localStorage.setItem(PAGE_SIZE_STORAGE_KEY, String(size))
  } catch {
    /* ignore */
  }
}

function coverUrlFor(file) {
  return API.coverFileURL(file)
}

function markCoverFailed(file) {
  coverFailed.value = { ...coverFailed.value, [file]: true }
}

function scheduleLoad() {
  if (filterDebounce) clearTimeout(filterDebounce)
  filterDebounce = setTimeout(() => {
    filterDebounce = null
    loadPage()
  }, 300)
}

function onPageChange(page) {
  currentPage.value = page
  loadPage()
}

async function loadPage({ refresh = false } = {}) {
  loading.value = true
  error.value = ''
  try {
    const res = await API.listDownloadsPage({
      page: currentPage.value,
      limit: pageSize.value,
      q: libraryFilterQuery.value,
      playlist: playlistFilter.value,
      refresh,
    })
    const data = res.data || {}
    files.value = (data.items || []).map(normalizeLibraryEntry)
    totalItems.value = Number(data.total) || 0
    pathsScanning.value = Boolean(data.paths_scanning)
    if (Array.isArray(data.playlist_names) && data.playlist_names.length) {
      playlistNames.value = data.playlist_names
    }
    if (currentPage.value > totalPages.value) {
      currentPage.value = totalPages.value
      if (currentPage.value >= 1) {
        await loadPage({ refresh: false })
      }
    }
  } catch {
    error.value = t('library.failedLoad')
  } finally {
    loading.value = false
  }
}

async function refresh() {
  currentPage.value = 1
  await loadPage({ refresh: true })
}

async function fetchAllFilteredEntries() {
  const items = []
  let page = 1
  let total = 1
  while (items.length < total) {
    const res = await API.listDownloadsPage({
      page,
      limit: 200,
      q: libraryFilterQuery.value,
      playlist: playlistFilter.value,
    })
    const data = res.data || {}
    items.push(...(data.items || []).map(normalizeLibraryEntry))
    total = Number(data.total) || items.length
    page += 1
    if (page > 100) break
  }
  return items
}

async function onDelete(file) {
  if (!confirm(t('library.deletePrompt', { file }))) return
  deleting.value = { ...deleting.value, [file]: true }
  error.value = ''
  try {
    const res = await API.deleteDownload(file)
    if (res.data?.deleted === false) {
      error.value = res.data?.error || t('library.failedDelete', { file })
      return
    }
    removeFilesFromList([file])
  } catch (err) {
    const detail = err?.response?.data?.error
    error.value =
      typeof detail === 'string' && detail
        ? detail
        : t('library.failedDelete', { file })
  } finally {
    deleting.value = { ...deleting.value, [file]: false }
  }
}

async function onDeleteSelected() {
  const paths = [...selectedFiles.value]
  if (!paths.length) return
  if (!confirm(t('library.deleteSelectedPrompt', { count: paths.length })))
    return
  batchDeleting.value = true
  error.value = ''
  try {
    const res = await API.deleteDownloadsBatch(paths)
    const deleted = res.data?.deleted || []
    const failed = res.data?.failed || []
    removeFilesFromList(deleted)
    if (failed.length) {
      error.value = t('library.batchDeletePartial', {
        ok: deleted.length,
        failed: failed.length,
      })
    }
  } catch (err) {
    const detail = err?.response?.data?.detail
    error.value =
      typeof detail === 'string' && detail
        ? detail
        : t('library.failedDelete', { file: paths[0] })
  } finally {
    batchDeleting.value = false
  }
}

async function onDeletePlaylist() {
  const name = String(playlistFilter.value || '').trim()
  if (!name) return
  if (!confirm(t('library.deletePlaylistPrompt', { name }))) return
  playlistDeleting.value = true
  error.value = ''
  try {
    const res = await API.deleteLibraryPlaylist(name)
    const count = res.data?.deleted_count ?? 0
    selectedFiles.value = new Set()
    playlistFilter.value = ''
    await loadPage()
    if ((res.data?.failed_count || 0) > 0) {
      error.value = t('library.batchDeletePartial', {
        ok: count,
        failed: res.data.failed_count,
      })
    }
  } catch (err) {
    const detail = err?.response?.data?.detail
    error.value =
      typeof detail === 'string' && detail
        ? detail
        : t('library.playlistDeleteFailed', { name })
  } finally {
    playlistDeleting.value = false
  }
}

function formatExt(file) {
  const dot = file.lastIndexOf('.')
  return dot > 0 ? file.slice(dot + 1).toUpperCase() : ''
}

function folderOf(file) {
  const slash = file.lastIndexOf('/')
  return slash >= 0 ? file.slice(0, slash) : ''
}

function persistPlayerViewForPlayback() {
  savePlayerViewPrefs({
    playlistFilter: playlistFilter.value,
    filterQuery: libraryFilterQuery.value,
  })
}

async function playEntry(entry) {
  const tracks = await fetchAllFilteredEntries()
  const index = tracks.findIndex((row) => row.file === entry.file)
  if (index < 0) return
  persistPlayerViewForPlayback()
  player.setPlaylist(tracks, { startIndex: index, autoplay: true })
  router.push({ name: 'Player' })
}

async function playAll() {
  const tracks = await fetchAllFilteredEntries()
  if (!tracks.length) return
  persistPlayerViewForPlayback()
  player.setPlaylist(tracks, { startIndex: 0, autoplay: true })
  router.push({ name: 'Player' })
}

onMounted(() => loadPage())

onUnmounted(() => {
  clearLibraryFilter()
})
</script>
