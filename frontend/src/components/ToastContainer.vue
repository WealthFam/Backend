<script setup lang="ts">
import { useNotificationStore } from '@/stores/notification'
import { CheckCircle, AlertCircle, Info, X } from 'lucide-vue-next'

const store = useNotificationStore()
</script>

<template>
    <div class="toast-container">
        <transition-group name="toast">
            <div v-for="note in store.notifications" :key="note.id" class="toast" :class="note.type"
                @click="store.remove(note.id)">
                <div class="icon-wrapper">
                    <CheckCircle v-if="note.type === 'success'" :size="20" class="text-success" />
                    <AlertCircle v-if="note.type === 'error'" :size="20" class="text-error" />
                    <Info v-if="note.type === 'info'" :size="20" class="text-primary" />
                </div>
                <div class="content">{{ note.message }}</div>
                <button class="close-btn">
                    <X :size="14" class="text-medium-emphasis" />
                </button>
            </div>
        </transition-group>
    </div>
</template>

<style scoped>
.toast-container {
    position: fixed;
    bottom: 2rem;
    right: 2rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    z-index: 9999;
    pointer-events: none;
}

.toast {
    pointer-events: auto;
    min-width: 320px;
    max-width: 400px;
    padding: 1rem;
    border-radius: 12px;
    background: rgb(var(--v-theme-surface));
    color: rgb(var(--v-theme-on-surface));
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
    display: flex;
    align-items: center;
    gap: 0.75rem;
    cursor: pointer;
    border: 1px solid rgba(var(--v-border-color), 0.1);
    position: relative;
    overflow: hidden;
    backdrop-filter: blur(10px);
}

/* Status variants with left colored accent */
.toast::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 4px;
}

.toast.success::before {
    background: rgb(var(--v-theme-success));
}

.toast.error::before {
    background: rgb(var(--v-theme-error));
}

.toast.info::before {
    background: rgb(var(--v-theme-primary));
}

/* Subtle tint based on type */
.toast.success {
    background: linear-gradient(to right, rgba(var(--v-theme-success), 0.05), rgb(var(--v-theme-surface)));
}

.toast.error {
    background: linear-gradient(to right, rgba(var(--v-theme-error), 0.05), rgb(var(--v-theme-surface)));
}

.toast.info {
    background: linear-gradient(to right, rgba(var(--v-theme-primary), 0.05), rgb(var(--v-theme-surface)));
}

.content {
    font-size: 0.9rem;
    font-weight: 500;
    line-height: 1.4;
    flex-grow: 1;
}

.close-btn {
    background: transparent;
    border: none;
    cursor: pointer;
    opacity: 0.5;
    transition: opacity 0.2s;
    display: flex;
    align-items: center;
}

.close-btn:hover {
    opacity: 1;
}

/* Text Colors */
.text-success {
    color: rgb(var(--v-theme-success));
}

.text-error {
    color: rgb(var(--v-theme-error));
}

.text-primary {
    color: rgb(var(--v-theme-primary));
}

.text-medium-emphasis {
    color: rgba(var(--v-theme-on-surface), 0.6);
}

/* Animation */
.toast-enter-active,
.toast-leave-active {
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.toast-enter-from,
.toast-leave-to {
    opacity: 0;
    transform: translateX(30px) scale(0.95);
}
</style>
