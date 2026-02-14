<template>
    <v-container fluid class="pa-0 animate-in relative-pos z-10">
        <!-- Stats Overview -->
        <v-row class="mb-8">
            <v-col cols="12" sm="6" md="3">
                <v-card @click="categoriesStore.searchFilter = 'all'"
                    class="premium-glass-card pa-6 h-100 cursor-pointer" rounded="xl">
                    <div class="d-flex justify-space-between align-center mb-4">
                        <span class="text-overline font-weight-black opacity-60 letter-spacing-1">Total</span>
                        <v-avatar color="indigo-lighten-5" rounded="lg" size="44">
                            <span class="text-h5">📊</span>
                        </v-avatar>
                    </div>
                    <div class="text-h4 font-weight-black">
                        {{ categoriesStore.categoryStats.total }}
                    </div>
                </v-card>
            </v-col>

            <v-col cols="12" sm="6" md="3">
                <v-card @click="categoriesStore.searchFilter = 'expense'"
                    class="premium-glass-card pa-6 h-100 cursor-pointer" rounded="xl"
                    :class="{ 'border-error': categoriesStore.searchFilter === 'expense' }">
                    <div class="d-flex justify-space-between align-center mb-4">
                        <span class="text-overline font-weight-black opacity-60 letter-spacing-1">Expenses</span>
                        <v-avatar color="rose-lighten-5" rounded="lg" size="44">
                            <span class="text-h5">💸</span>
                        </v-avatar>
                    </div>
                    <div class="text-h4 font-weight-black"
                        :class="categoriesStore.searchFilter === 'expense' ? 'text-error' : ''">
                        {{ categoriesStore.categoryStats.expenses }}
                    </div>
                </v-card>
            </v-col>

            <v-col cols="12" sm="6" md="3">
                <v-card @click="categoriesStore.searchFilter = 'income'"
                    class="premium-glass-card pa-6 h-100 cursor-pointer" rounded="xl"
                    :class="{ 'border-success': categoriesStore.searchFilter === 'income' }">
                    <div class="d-flex justify-space-between align-center mb-4">
                        <span class="text-overline font-weight-black opacity-60 letter-spacing-1">Income</span>
                        <v-avatar color="emerald-lighten-5" rounded="lg" size="44">
                            <span class="text-h5">💰</span>
                        </v-avatar>
                    </div>
                    <div class="text-h4 font-weight-black"
                        :class="categoriesStore.searchFilter === 'income' ? 'text-success' : ''">
                        {{ categoriesStore.categoryStats.income }}
                    </div>
                </v-card>
            </v-col>

            <v-col cols="12" sm="6" md="3">
                <v-card @click="categoriesStore.searchFilter = 'transfer'"
                    class="premium-glass-card pa-6 h-100 cursor-pointer" rounded="xl"
                    :class="{ 'border-info': categoriesStore.searchFilter === 'transfer' }">
                    <div class="d-flex justify-space-between align-center mb-4">
                        <span class="text-overline font-weight-black opacity-60 letter-spacing-1">Transfers</span>
                        <v-avatar color="cyan-lighten-5" rounded="lg" size="44">
                            <span class="text-h5">🔄</span>
                        </v-avatar>
                    </div>
                    <div class="text-h4 font-weight-black"
                        :class="categoriesStore.searchFilter === 'transfer' ? 'text-info' : ''">
                        {{ categoriesStore.categoryStats.transfer }}
                    </div>
                </v-card>
            </v-col>
        </v-row>

        <!-- Tool Bar (Glass Box) -->
        <v-card class="premium-glass-card pa-4 mb-8 no-hover" rounded="xl">
            <v-row align="center">
                <v-col cols="12" md="4">
                    <v-text-field v-model="categoriesStore.searchQuery" placeholder="Search categories..." hide-details
                        density="comfortable" variant="plain" class="font-weight-bold px-2">
                        <template v-slot:prepend-inner>
                            <Search :size="20" class="text-slate-400" />
                        </template>
                    </v-text-field>
                </v-col>

                <v-spacer />

                <v-col cols="12" md="auto" class="d-flex align-center gap-3">
                    <div class="glass-card border rounded-pill d-flex align-center pa-1"
                        style="background: rgba(var(--v-theme-surface), 0.5)">
                        <v-btn variant="text" size="small" rounded="pill" color="primary"
                            class="text-none font-weight-black" @click="categoriesStore.exportCategories">
                            <template v-slot:prepend>
                                <Download :size="16" />
                            </template>
                            Export
                        </v-btn>
                        <v-divider vertical class="mx-1 my-1 opacity-20" />
                        <v-btn variant="text" size="small" rounded="pill" color="primary"
                            class="text-none font-weight-black" @click="triggerImport">
                            <template v-slot:prepend>
                                <Upload :size="16" />
                            </template>
                            Import
                        </v-btn>
                    </div>
                </v-col>
            </v-row>
        </v-card>

        <!-- Invisible file input for import -->
        <input type="file" ref="fileInput" accept=".json" style="display: none" @change="handleImportCategories" />

        <!-- Categories Grid -->
        <div v-if="categoriesStore.loading" class="d-flex justify-center py-12">
            <v-skeleton-loader type="card" width="100%" height="200" v-for="i in 4" :key="i" class="ma-2"
                rounded="xl" />
        </div>

        <v-row v-else class="pb-16">
            <!-- Add New Card -->
            <v-col cols="12" sm="6" md="4" lg="3">
                <v-card @click="startAddCategory"
                    class="premium-glass-card d-flex flex-column align-center justify-center h-100 cursor-pointer border-dashed border-primary group"
                    style="border-width: 2px !important; min-height: 258px; background: rgba(var(--v-theme-primary), 0.05)"
                    rounded="xl">
                    <v-avatar color="primary" size="64" class="mb-4 elevation-8 group-on-hover-scale"
                        style="box-shadow: 0 0 20px rgba(var(--v-theme-primary), 0.3)">
                        <Plus :size="36" color="white" stroke-width="3" />
                    </v-avatar>
                    <span class="text-h6 font-weight-black text-primary">Add New Category</span>
                    <span class="text-caption font-weight-bold opacity-60 text-slate-500">Create a root folder</span>
                </v-card>
            </v-col>

            <!-- Categories -->
            <v-col v-for="cat in categoriesStore.rootCategories" :key="cat.id" cols="12" sm="6" md="4" lg="3">
                <v-card class="premium-glass-card h-100 d-flex flex-column overflow-hidden" rounded="xl">
                    <div class="pa-6 d-flex align-start relative-pos z-10">
                        <v-avatar :color="cat.color + '25'" rounded="lg" size="52" border class="elevation-2 me-4">
                            <span class="text-h4" :style="{ color: cat.color }">{{ cat.icon || '🏷️' }}</span>
                        </v-avatar>
                        <div class="min-w-0 flex-grow-1">
                            <div class="text-h6 font-weight-black truncate mb-1">{{ cat.name }}</div>
                            <v-chip density="comfortable" size="x-small"
                                class="text-uppercase font-weight-black letter-spacing-1" variant="tonal"
                                :color="cat.type === 'income' ? 'success' : (cat.type === 'transfer' ? 'info' : 'primary')"
                                label>
                                {{ cat.type || 'expense' }}
                            </v-chip>
                        </div>
                    </div>

                    <!-- Subcategories -->
                    <div class="px-4 pb-4 flex-grow-1">
                        <div v-if="categoriesStore.getChildren(cat.id).length > 0"
                            class="d-flex flex-column gap-2 mt-2">
                            <div v-for="child in categoriesStore.getChildren(cat.id)" :key="child.id"
                                class="inset-glass-metric pa-2 px-3 border-thin group cursor-pointer rounded-lg relative-pos overflow-hidden"
                                style="background: rgba(var(--v-theme-surface), 0.4)" @click.stop="editCategory(child)">
                                <div class="d-flex justify-space-between align-center relative-pos z-2">
                                    <div class="d-flex align-center gap-2">
                                        <span class="text-body-2">{{ child.icon }}</span>
                                        <span class="text-body-2 font-weight-black truncate">{{ child.name }}</span>
                                    </div>
                                    <div class="d-flex gap-1 transition-all duration-200">
                                        <v-btn variant="outlined" size="x-small"
                                            class="rounded-lg border-thin bg-surface-light opacity-60 hover-opacity-100"
                                            style="min-width: 28px; width: 28px; height: 28px; padding: 0"
                                            @click.stop="editCategory(child)">
                                            <Pencil :size="12" />
                                            <v-tooltip activator="parent" location="top">Edit Sub</v-tooltip>
                                        </v-btn>
                                        <v-btn variant="outlined" color="error" size="x-small"
                                            class="rounded-lg border-thin bg-surface-light opacity-60 hover-opacity-100"
                                            style="min-width: 28px; width: 28px; height: 28px; padding: 0"
                                            @click.stop="startDeleteCategory(child)">
                                            <Trash2 :size="12" />
                                            <v-tooltip activator="parent" location="top">Delete Sub</v-tooltip>
                                        </v-btn>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div v-else class="d-flex flex-column align-center justify-center py-6 opacity-30 mt-4">
                            <Layers :size="32" class="mb-2" />
                            <span class="text-caption font-weight-bold">No Sub-categories</span>
                        </div>
                    </div>

                    <v-divider class="opacity-10" :thickness="1" />

                    <!-- Bottom Toolbar (Refined Aesthetics) -->
                    <div class="pa-4 d-flex align-center justify-space-between bg-transparent">
                        <v-btn variant="outlined" color="primary"
                            class="rounded-lg border-thin font-weight-black text-none"
                            style="height: 36px; min-width: 36px; padding: 0" @click.stop="startAddSubCategory(cat)">
                            <Plus :size="18" />
                            <v-tooltip activator="parent" location="top">Add Sub</v-tooltip>
                        </v-btn>
                        <div class="d-flex gap-2">
                            <v-btn variant="outlined" color="slate-600" class="rounded-lg border-thin"
                                style="height: 36px; min-width: 36px; padding: 0" @click.stop="editCategory(cat)">
                                <Pencil :size="18" />
                                <v-tooltip activator="parent" location="top">Edit</v-tooltip>
                            </v-btn>
                            <v-btn variant="outlined" color="error" class="rounded-lg border-thin"
                                style="height: 36px; min-width: 36px; padding: 0"
                                @click.stop="startDeleteCategory(cat)">
                                <Trash2 :size="18" />
                                <v-tooltip activator="parent" location="top">Delete</v-tooltip>
                            </v-btn>
                        </div>
                    </div>

                    <!-- Subtle background icon -->
                    <div class="card-bg-icon-standard">
                        <Folder :size="120" />
                    </div>
                </v-card>
            </v-col>
        </v-row>

        <!-- Add/Edit Category Modal -->
        <v-dialog v-model="showCategoryModal" max-width="500px" persistent>
            <v-card class="premium-glass-card no-hover" rounded="xl">
                <v-card-title class="pa-6 border-b d-flex align-center">
                    <div class="d-flex align-center gap-3 flex-grow-1">
                        <v-avatar :color="categoryForm.color" rounded="lg" size="44" class="elevation-4">
                            <span class="text-h4 text-white">{{ categoryForm.icon || '🏷️' }}</span>
                        </v-avatar>
                        <div>
                            <div class="text-overline font-weight-black opacity-60 line-height-1 mb-1">
                                {{ isEditingCategory ? 'Update' : 'Configure' }}
                            </div>
                            <div class="text-h6 font-weight-black line-height-1 truncate" style="max-width: 250px;">
                                {{ previewName }}
                            </div>
                        </div>
                    </div>
                    <v-btn icon variant="text" size="small" @click="showCategoryModal = false" color="slate-400">
                        <X :size="20" />
                    </v-btn>
                </v-card-title>

                <v-card-text class="pa-6">
                    <v-form @submit.prevent="saveCategory">
                        <v-row>
                            <v-col cols="4">
                                <v-text-field v-model="categoryForm.icon" label="Icon" variant="outlined" rounded="lg"
                                    placeholder="Emoji" hide-details class="font-weight-black text-h5"
                                    density="comfortable" />
                            </v-col>
                            <v-col cols="8">
                                <v-text-field v-model="categoryForm.name" label="Name" variant="outlined" rounded="lg"
                                    required placeholder="e.g. Subscriptions" hide-details
                                    class="font-weight-black text-h6" density="comfortable" />
                            </v-col>

                            <v-col cols="12">
                                <v-select v-model="categoryForm.parent_id" label="Parent Category (Optional)"
                                    variant="outlined" rounded="lg" :items="parentOptions" item-title="title"
                                    item-value="value" hide-details density="comfortable"
                                    class="font-weight-bold premium-modal-select"
                                    style="background: rgba(var(--v-theme-surface), 0.7);">
                                    <template v-slot:append-inner>
                                        <ChevronDown :size="16" class="text-primary opacity-70" />
                                    </template>
                                </v-select>
                            </v-col>

                            <v-col cols="12">
                                <v-select v-model="categoryForm.type" label="Financial Type" variant="outlined"
                                    rounded="lg" :items="[
                                        { title: '🔴 Expense', value: 'expense' },
                                        { title: '🟢 Income', value: 'income' },
                                        { title: '🔄 Transfer', value: 'transfer' }
                                    ]" hide-details density="comfortable" class="font-weight-bold premium-modal-select"
                                    style="background: rgba(var(--v-theme-surface), 0.7);">
                                    <template v-slot:append-inner>
                                        <ChevronDown :size="16" class="text-primary opacity-70" />
                                    </template>
                                </v-select>
                            </v-col>

                            <v-col cols="12">
                                <div class="text-subtitle-2 font-weight-black mb-3 opacity-60">THEME COLOR</div>
                                <div class="glass-card pa-4 border d-flex flex-wrap gap-3 align-center">
                                    <v-btn v-for="c in colorPresets" :key="c" :color="c" icon size="x-small"
                                        @click="categoryForm.color = c" :elevation="categoryForm.color === c ? 8 : 0"
                                        :class="{ 'border-xl border-white': categoryForm.color === c }"
                                        style="width: 28px; height: 28px;" />
                                    <v-divider vertical class="mx-2" height="24" />
                                    <div class="relative-pos">
                                        <input type="color" v-model="categoryForm.color" class="custom-color-input" />
                                    </div>
                                </div>
                            </v-col>
                        </v-row>
                    </v-form>
                </v-card-text>

                <v-card-actions class="pa-6 pt-0">
                    <v-spacer />
                    <v-btn variant="text" @click="showCategoryModal = false" class="text-none px-8 font-weight-black"
                        rounded="pill">Cancel</v-btn>
                    <v-btn color="primary" rounded="pill" class="text-none px-10 btn-primary-glow font-weight-black"
                        @click="saveCategory" size="large">
                        {{ isEditingCategory ? 'Save Changes' : 'Create Category' }}
                    </v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>

        <!-- Delete Confirmation Modal -->
        <v-dialog v-model="showDeleteCategoryConfirm" max-width="450px" persistent>
            <v-card class="premium-glass-card no-hover text-center pa-8" rounded="xl">
                <v-avatar color="error" variant="tonal" size="80" class="mb-6 mx-auto">
                    <AlertCircle :size="48" />
                </v-avatar>
                <h3 class="text-h5 font-weight-black mb-2">Delete Category?</h3>
                <p class="text-subtitle-1 font-weight-medium opacity-60 mb-8">
                    Existing transactions will become uncategorized. This action is permanent and affects your financial
                    history.
                </p>
                <v-row>
                    <v-col cols="6">
                        <v-btn block variant="text" rounded="pill" class="text-none font-weight-black" height="48"
                            @click="showDeleteCategoryConfirm = false">No, Keep</v-btn>
                    </v-col>
                    <v-col cols="6">
                        <v-btn block color="error" rounded="pill" class="text-none font-weight-black elevation-4"
                            height="48" @click="confirmDeleteCategory">Yes, Delete</v-btn>
                    </v-col>
                </v-row>
            </v-card>
        </v-dialog>

        <!-- Delete Restricted Modal -->
        <v-dialog v-model="showDeleteRestrictedModal" max-width="450px" persistent>
            <v-card class="premium-glass-card no-hover text-center pa-8" rounded="xl">
                <v-avatar color="warning" variant="tonal" size="80" class="mb-6 mx-auto">
                    <AlertCircle :size="48" />
                </v-avatar>
                <h3 class="text-h5 font-weight-black mb-2">Notice</h3>
                <p class="text-subtitle-1 font-weight-medium opacity-60 mb-8">
                    This category contains active sub-categories. You need to delete or move all children before you can
                    remove this parent folder.
                </p>
                <v-btn block color="primary" rounded="pill" class="text-none font-weight-black" height="48"
                    @click="showDeleteRestrictedModal = false">Understand</v-btn>
            </v-card>
        </v-dialog>
    </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useCategoriesStore } from '@/stores/finance/categories'
import {
    Search, Plus, Pencil, Trash2, Folder, Layers,
    Download, Upload, AlertCircle, X, ChevronDown
} from 'lucide-vue-next'

const categoriesStore = useCategoriesStore()

// Local UI State (Modals)
const showCategoryModal = ref(false)
const isEditingCategory = ref(false)
const editingCategoryId = ref<string | null>(null)
const showDeleteCategoryConfirm = ref(false)
const showDeleteRestrictedModal = ref(false)
const categoryToDelete = ref<any>(null)
const fileInput = ref<HTMLInputElement | null>(null)

function triggerImport() {
    fileInput.value?.click()
}

function handleImportCategories(event: Event) {
    const file = (event.target as HTMLInputElement).files?.[0]
    if (file) {
        categoriesStore.importCategories(file)
    }
    if (fileInput.value) fileInput.value.value = ''
}

const categoryForm = ref({
    name: '',
    icon: '🏷️',
    color: '#3B82F6',
    type: 'expense',
    parent_id: null as string | null
})

const previewName = computed(() => categoryForm.value.name || 'New Category')

const parentOptions = computed(() => {
    return [
        { title: 'None (Root Category)', value: null },
        ...categoriesStore.categories
            .filter(c => c.id !== editingCategoryId.value && !c.parent_id)
            .map(c => ({ title: `${c.icon} ${c.name}`, value: c.id }))
    ]
})

const colorPresets = [
    '#4F46E5', '#10B981', '#F59E0B', '#F43F5E', '#8B5CF6',
    '#EC4899', '#06B6D4', '#F97316', '#6366F1', '#1e293b'
]

onMounted(() => {
    categoriesStore.fetchCategories()
})

function startAddCategory() {
    isEditingCategory.value = false
    editingCategoryId.value = null
    categoryForm.value = {
        name: '',
        icon: '🏷️',
        color: '#4F46E5',
        type: 'expense',
        parent_id: null
    }
    showCategoryModal.value = true
}

function startAddSubCategory(parent: any) {
    isEditingCategory.value = false
    editingCategoryId.value = null
    categoryForm.value = {
        name: '',
        icon: '🏷️',
        color: parent.color,
        type: parent.type,
        parent_id: parent.id
    }
    showCategoryModal.value = true
}

function editCategory(cat: any) {
    isEditingCategory.value = true
    editingCategoryId.value = cat.id
    categoryForm.value = { ...cat }
    showCategoryModal.value = true
}

async function saveCategory() {
    let success = false
    if (isEditingCategory.value && editingCategoryId.value) {
        success = await categoriesStore.updateCategory(editingCategoryId.value, categoryForm.value)
    } else {
        success = await categoriesStore.createCategory(categoryForm.value)
    }

    if (success) {
        showCategoryModal.value = false
    }
}

function startDeleteCategory(cat: any) {
    if (categoriesStore.getChildren(cat.id).length > 0) {
        showDeleteRestrictedModal.value = true
    } else {
        categoryToDelete.value = cat
        showDeleteCategoryConfirm.value = true
    }
}

async function confirmDeleteCategory() {
    if (!categoryToDelete.value) return
    const success = await categoriesStore.deleteCategory(categoryToDelete.value.id)
    if (success) {
        showDeleteCategoryConfirm.value = false
        categoryToDelete.value = null
    }
}

// Expose open modal method
defineExpose({
    startAddCategory
})
</script>

<style scoped>
.custom-color-input {
    width: 32px;
    height: 32px;
    padding: 2px;
    border: 1px solid rgba(var(--v-border-color), 0.2);
    border-radius: 8px;
    cursor: pointer;
    background: rgba(var(--v-theme-surface), 0.5);
}

.custom-color-input::-webkit-color-swatch-wrapper {
    padding: 0;
}

.custom-color-input::-webkit-color-swatch {
    border: none;
    border-radius: 6px;
}

.card-bg-icon-standard {
    position: absolute;
    bottom: -1.5rem;
    right: -1rem;
    font-size: 8rem;
    opacity: 0.03;
    pointer-events: none;
    line-height: 1;
    transform: rotate(-12deg);
    transition: all 0.5s ease;
    z-index: 0;
}

.premium-glass-card:hover .card-bg-icon-standard {
    transform: rotate(0deg) scale(1.1);
    opacity: 0.05;
}

.group:hover .opacity-0 {
    opacity: 1 !important;
}

.border-dashed {
    border-style: dashed !important;
}

.border-primary {
    border-color: rgba(var(--v-theme-primary), 0.5) !important;
    border-width: 2px !important;
}

.border-error {
    border-color: rgba(var(--v-theme-error), 0.5) !important;
    border-width: 2px !important;
}

.border-success {
    border-color: rgba(var(--v-theme-success), 0.5) !important;
    border-width: 2px !important;
}

.border-info {
    border-color: rgba(var(--v-theme-info), 0.5) !important;
    border-width: 2px !important;
}

@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }

    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.group-on-hover-scale {
    transition: transform 0.3s ease;
}

.group:hover .group-on-hover-scale {
    transform: scale(1.1);
}

.hover-opacity-100:hover {
    opacity: 1 !important;
}

.border-thin {
    border: 1px solid rgba(var(--v-border-color), 0.15) !important;
}

.premium-modal-select :deep(.v-field__outline) {
    --v-field-border-opacity: 0.1;
    transition: border-color 0.3s ease;
}

.premium-modal-select:hover :deep(.v-field__outline) {
    --v-field-border-opacity: 0.4;
    border-color: rgb(var(--v-theme-primary)) !important;
}

.transition-all {
    transition: all 0.3s ease;
}
</style>
