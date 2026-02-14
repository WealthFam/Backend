<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'

const props = defineProps<{
    modelValue: any
    options: Array<{ label: string, value: any }>
    placeholder?: string
    label?: string
    required?: boolean
    allowNew?: boolean
}>()

const emit = defineEmits(['update:modelValue'])

const isOpen = ref(false)
const searchQuery = ref('')
const searchInputRef = ref<HTMLInputElement | null>(null)

const filteredOptions = computed(() => {
    if (!searchQuery.value) return props.options
    const query = searchQuery.value.toLowerCase()
    return props.options.filter(o =>
        o.label.toLowerCase().includes(query) ||
        String(o.value).toLowerCase().includes(query)
    )
})

const selectedLabel = computed(() => {
    const opt = props.options.find(o => o.value === props.modelValue)
    return opt ? opt.label : (props.placeholder || 'Select an option')
})

function select(value: any) {
    emit('update:modelValue', value)
    isOpen.value = false
    searchQuery.value = ''
}

// Watch isOpen to focus search
watch(isOpen, (val) => {
    if (val) {
        searchQuery.value = ''
        nextTick(() => {
            searchInputRef.value?.focus()
        })
    }
})
</script>

<template>
    <div class="custom-select-container">
        <v-menu v-model="isOpen" :close-on-content-click="false" location="bottom" offset="5"
            content-class="custom-select-menu">
            <template v-slot:activator="{ props }">
                <div class="select-trigger" :class="{ 'open': isOpen, 'placeholder': !modelValue }" v-bind="props"
                    tabindex="0">
                    <span class="truncate">{{ selectedLabel }}</span>
                    <span class="chevron">▼</span>
                </div>
            </template>

            <div class="options-container">
                <div class="search-box">
                    <input ref="searchInputRef" type="text" v-model="searchQuery" placeholder="Search..."
                        class="search-input" @keydown.esc="isOpen = false" />
                    <span class="search-icon">🔍</span>
                </div>

                <div class="options-list">
                    <div v-for="opt in filteredOptions" :key="opt.value" class="option-item"
                        :class="{ 'selected': opt.value === modelValue }" @click="select(opt.value)">
                        <span class="truncate">{{ opt.label }}</span>
                        <span v-if="opt.value === modelValue" class="check">✓</span>
                    </div>

                    <div v-if="filteredOptions.length === 0" class="no-results">
                        No matches found
                    </div>
                </div>
            </div>
        </v-menu>
    </div>
</template>

<style scoped>
.custom-select-container {
    width: 100%;
}

.select-trigger {
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
    user-select: none;
    background: white;
    min-height: 2.5rem;
    padding: 0.5rem 0.875rem;
    position: relative;
    border: 1px solid #e2e8f0;
    /* var(--color-border) fallback */
    border-radius: 0.5rem;
    font-family: inherit;
    font-size: 1rem;
    /* var(--font-size-base) */
    color: #0f172a;
    /* var(--color-text-main) */
    transition: all 0.3s ease;
}

.select-trigger:focus {
    outline: none;
    border-color: #4f46e5;
    /* var(--color-primary) */
    box-shadow: 0 0 0 3px #e0e7ff;
    /* var(--color-primary-light) */
}

.truncate {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 90%;
}

.select-trigger.placeholder {
    color: #9ca3af;
}

.chevron {
    font-size: 0.7rem;
    color: #9ca3af;
    transition: transform 0.2s;
    float: right;
}

.select-trigger.open .chevron {
    transform: rotate(180deg);
}

.options-container {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 0.75rem;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.2), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
    overflow: hidden;
    display: flex;
    flex-direction: column;
    min-width: 200px;
    /* Static positioning for v-menu content */
}

.search-box {
    padding: 0.75rem;
    border-bottom: 1px solid #f3f4f6;
    background: #f9fafb;
    position: relative;
}

.search-input {
    width: 100%;
    padding: 0.5rem 0.75rem 0.5rem 2rem;
    font-size: 0.875rem;
    border: 1px solid #e5e7eb;
    border-radius: 0.5rem;
    outline: none;
    transition: all 0.2s;
}

.search-input:focus {
    border-color: #4f46e5;
    box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.1);
}

.search-icon {
    position: absolute;
    left: 1.25rem;
    top: 50%;
    transform: translateY(-50%);
    font-size: 0.8rem;
    opacity: 0.4;
}

.options-list {
    max-height: 250px;
    overflow-y: auto;
    padding: 0.25rem;
}

.option-item {
    padding: 0.625rem 0.875rem;
    cursor: pointer;
    border-radius: 0.5rem;
    color: #374151;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.875rem;
    transition: all 0.1s;
}

.option-item:hover {
    background: #f3f4f6;
    color: #111827;
}

.option-item.selected {
    background: #eef2ff;
    color: #4f46e5;
    font-weight: 600;
}

.no-results {
    padding: 1.5rem;
    text-align: center;
    color: #9ca3af;
    font-size: 0.875rem;
}

.check {
    font-size: 0.8rem;
    margin-left: 0.5rem;
}

/* Scrollbar */
.options-list::-webkit-scrollbar {
    width: 6px;
}

.options-list::-webkit-scrollbar-track {
    background: transparent;
}

.options-list::-webkit-scrollbar-thumb {
    background: #e5e7eb;
    border-radius: 3px;
}
</style>
