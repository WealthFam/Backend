<script setup lang="ts">
import { useConfirmStore } from '@/stores/confirm'

const confirm = useConfirmStore()
</script>

<template>
  <v-dialog v-model="confirm.isOpen" max-width="400" persistent>
    <v-card class="rounded-xl elevation-24 border" style="background: rgba(var(--v-theme-surface), 0.95); backdrop-filter: blur(10px);">
      <v-card-title class="text-h6 font-weight-bold pt-4 px-6 mb-2">
        <v-icon color="warning" class="mr-2 mb-1">mdi-alert-circle-outline</v-icon>
        {{ confirm.title }}
      </v-card-title>
      
      <v-card-text class="text-body-1 px-6 pb-6 text-medium-emphasis">
        {{ confirm.message }}
      </v-card-text>
      
      <v-divider></v-divider>
      
      <v-card-actions class="pa-4 bg-surface-light">
        <v-spacer></v-spacer>
        <v-btn 
          color="medium-emphasis" 
          variant="text" 
          class="text-none font-weight-bold px-4 mr-2 rounded-lg"
          @click="confirm.cancel()"
        >
          {{ confirm.cancelText }}
        </v-btn>
        
        <v-btn 
          color="error" 
          variant="flat" 
          class="text-none font-weight-bold px-6 rounded-lg elevation-2"
          @click="confirm.agree()"
        >
          {{ confirm.confirmText }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped>
</style>
