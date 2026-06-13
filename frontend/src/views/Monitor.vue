<template>
  <div class="min-h-dvh">
    <Navbar />
    <Settings />

    <div class="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <div class="mb-8">
        <h1 class="text-2xl font-bold tracking-tight">
          {{ t('monitor.title') }}
        </h1>
        <p class="mt-1 text-sm text-base-content/60">
          {{ t('monitor.subtitle') }}
        </p>
      </div>

      <IncompletePlaylists @download="queueTrack" />

      <div
        class="mt-8 surface rounded-2xl p-4 flex gap-3 text-sm text-base-content/60"
      >
        <Icon
          icon="clarity:info-standard-line"
          class="h-5 w-5 shrink-0 mt-0.5 text-primary/70"
        />
        <p>{{ t('monitor.info') }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Icon } from '@iconify/vue'
import Navbar from '../components/Navbar.vue'
import Settings from '../components/Settings.vue'
import IncompletePlaylists from '../components/IncompletePlaylists.vue'
import { useDownloadManager } from '../model/download'
import { useI18n } from '../i18n'

const { t } = useI18n()
const dm = useDownloadManager()

function queueTrack(track) {
  dm.queue(track)
}
</script>
