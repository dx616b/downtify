<template>
  <div class="space-y-2">
    <label
      class="flex items-center gap-2 cursor-pointer select-none text-xs text-base-content/70"
    >
      <input
        type="checkbox"
        class="checkbox checkbox-xs checkbox-primary"
        :checked="useGlobal"
        @change="onToggleGlobal($event)"
      />
      <span>{{ t('playlistProviders.useGlobal') }}</span>
    </label>

    <p v-if="useGlobal" class="text-[11px] text-base-content/50">
      {{
        t('playlistProviders.usingGlobal', {
          chain: providerChain(globalProviders),
        })
      }}
    </p>

    <template v-else>
      <div class="grid grid-cols-3 gap-1.5">
        <button
          v-for="provider in availableProviders"
          :key="provider"
          type="button"
          class="rounded-lg border px-2 py-1.5 text-[11px] transition-colors text-left relative"
          :class="[
            providerIndex(provider) >= 0
              ? 'border-primary/50 bg-primary/10 text-primary'
              : 'border-white/10 hover:border-white/20 hover:bg-white/5',
          ]"
          @click="toggleProvider(provider)"
        >
          <span
            v-if="providerIndex(provider) >= 0"
            class="absolute top-0.5 right-0.5 text-[9px] font-bold opacity-80"
          >
            {{ providerIndex(provider) + 1 }}
          </span>
          {{ providerLabel(provider) }}
        </button>
      </div>
      <p class="text-[10px] text-base-content/40">
        {{ t('playlistProviders.customHint') }}
      </p>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from '/src/i18n'

const props = defineProps({
  modelValue: {
    type: [Array, null],
    default: null,
  },
  globalProviders: {
    type: Array,
    default: () => ['youtube-music'],
  },
  slskdEnabled: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue'])

const { t } = useI18n()

const ALL_PROVIDERS = ['slskd', 'youtube-music', 'youtube']

const availableProviders = computed(() =>
  ALL_PROVIDERS.filter((p) => p !== 'slskd' || props.slskdEnabled)
)

const useGlobal = computed(() => props.modelValue == null)

function providerLabel(provider) {
  if (provider === 'youtube-music') return 'YT Music'
  if (provider === 'youtube') return 'YouTube'
  if (provider === 'slskd') return 'slskd'
  return provider
}

function providerChain(providers) {
  return (providers || []).map(providerLabel).join(' → ') || '—'
}

function providerIndex(provider) {
  const list = props.modelValue || []
  return list.indexOf(provider)
}

function onToggleGlobal(event) {
  if (event.target.checked) {
    emit('update:modelValue', null)
    return
  }
  const seed = [...(props.globalProviders || [])]
  emit('update:modelValue', seed.length ? seed : ['youtube-music'])
}

function toggleProvider(provider) {
  const list = [...(props.modelValue || [])]
  const idx = list.indexOf(provider)
  if (idx >= 0) {
    list.splice(idx, 1)
  } else {
    list.push(provider)
  }
  emit('update:modelValue', list.length ? list : ['youtube-music'])
}
</script>
