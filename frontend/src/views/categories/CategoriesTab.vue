<template>
    <v-container fluid class="pa-0 animate-in relative-pos z-10">
        <!-- Stats Overview -->
        <v-row class="mb-6">
            <v-col cols="12" sm="6" md="3">
                <v-card @click="categoriesStore.searchFilter = 'all'"
                    class="premium-glass-card pa-5 h-100 cursor-pointer border-thin elevation-2" rounded="xl">
                    <div class="d-flex justify-space-between align-start mb-2">
                        <div>
                            <span class="text-overline font-weight-black opacity-50 letter-spacing-2">Total</span>
                            <div class="text-h4 font-weight-black mt-1">
                                {{ categoriesStore.categoryStats.total }}
                            </div>
                        </div>
                        <v-avatar color="primary" variant="tonal" rounded="lg" size="48" class="elevation-1">
                            <BarChart3 :size="24" />
                        </v-avatar>
                    </div>
                    <div class="text-caption font-weight-bold opacity-60">Revenue & Expense items</div>
                </v-card>
            </v-col>

            <v-col cols="12" sm="6" md="3">
                <v-card @click="categoriesStore.searchFilter = 'expense'"
                    class="premium-glass-card pa-5 h-100 cursor-pointer border-thin elevation-2" rounded="xl"
                    :class="{ 'border-error': categoriesStore.searchFilter === 'expense' }">
                    <div class="d-flex justify-space-between align-start mb-2">
                        <div>
                            <span class="text-overline font-weight-black opacity-50 letter-spacing-2">Expenses</span>
                            <div class="text-h4 font-weight-black mt-1"
                                :class="categoriesStore.searchFilter === 'expense' ? 'text-error' : ''">
                                {{ categoriesStore.categoryStats.expenses }}
                            </div>
                        </div>
                        <v-avatar color="error" variant="tonal" rounded="lg" size="48" class="elevation-1">
                            <TrendingDown :size="24" />
                        </v-avatar>
                    </div>
                    <v-progress-linear
                        :model-value="(categoriesStore.categoryStats.expenses / categoriesStore.categoryStats.total) * 100"
                        color="error" height="4" rounded="pill" class="mt-2 opacity-30" />
                </v-card>
            </v-col>

            <v-col cols="12" sm="6" md="3">
                <v-card @click="categoriesStore.searchFilter = 'income'"
                    class="premium-glass-card pa-5 h-100 cursor-pointer border-thin elevation-2" rounded="xl"
                    :class="{ 'border-success': categoriesStore.searchFilter === 'income' }">
                    <div class="d-flex justify-space-between align-start mb-2">
                        <div>
                            <span class="text-overline font-weight-black opacity-50 letter-spacing-2">Income</span>
                            <div class="text-h4 font-weight-black mt-1"
                                :class="categoriesStore.searchFilter === 'income' ? 'text-success' : ''">
                                {{ categoriesStore.categoryStats.income }}
                            </div>
                        </div>
                        <v-avatar color="success" variant="tonal" rounded="lg" size="48" class="elevation-1">
                            <TrendingUp :size="24" />
                        </v-avatar>
                    </div>
                    <v-progress-linear
                        :model-value="(categoriesStore.categoryStats.income / categoriesStore.categoryStats.total) * 100"
                        color="success" height="4" rounded="pill" class="mt-2 opacity-30" />
                </v-card>
            </v-col>

            <v-col cols="12" sm="6" md="3">
                <v-card @click="categoriesStore.searchFilter = 'transfer'"
                    class="premium-glass-card pa-5 h-100 cursor-pointer border-thin elevation-2" rounded="xl"
                    :class="{ 'border-info': categoriesStore.searchFilter === 'transfer' }">
                    <div class="d-flex justify-space-between align-start mb-2">
                        <div>
                            <span class="text-overline font-weight-black opacity-50 letter-spacing-2">Transfers</span>
                            <div class="text-h4 font-weight-black mt-1"
                                :class="categoriesStore.searchFilter === 'transfer' ? 'text-info' : ''">
                                {{ categoriesStore.categoryStats.transfer }}
                            </div>
                        </div>
                        <v-avatar color="info" variant="tonal" rounded="lg" size="48" class="elevation-1">
                            <Repeat :size="24" />
                        </v-avatar>
                    </div>
                    <v-progress-linear
                        :model-value="(categoriesStore.categoryStats.transfer / categoriesStore.categoryStats.total) * 100"
                        color="info" height="4" rounded="pill" class="mt-2 opacity-30" />
                </v-card>
            </v-col>
        </v-row>

        <!-- Tool Bar -->
        <v-card class="premium-glass-card pa-3 mb-8 no-hover border-thin elevation-2" rounded="xl">
            <v-row align="center" dense>
                <v-col cols="12" md="4">
                    <v-text-field v-model="categoriesStore.searchQuery" placeholder="Search categories..." hide-details
                        density="compact" variant="solo-filled" flat rounded="lg" class="font-weight-bold"
                        bg-color="surface">
                        <template v-slot:prepend-inner>
                            <Search :size="18" class="text-primary mr-2 opacity-70" />
                        </template>
                    </v-text-field>
                </v-col>

                <v-spacer />

                <v-col cols="12" md="auto" class="d-flex align-center ga-3">
                    <div class="glass-card border rounded-pill d-flex align-center pa-1"
                        style="background: rgba(var(--v-theme-surface), 0.5)">
                        <v-btn variant="text" size="small" rounded="pill" color="primary"
                            class="text-none font-weight-black px-4" @click="categoriesStore.exportCategories">
                            <template v-slot:prepend>
                                <Download :size="14" />
                            </template>
                            Export
                        </v-btn>
                        <v-divider vertical class="mx-1 my-1 opacity-10" />
                        <v-btn variant="text" size="small" rounded="pill" color="primary"
                            class="text-none font-weight-black px-4" @click="triggerImport">
                            <template v-slot:prepend>
                                <Upload :size="14" />
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

        <v-row v-else class="pb-16 ga-y-6">
            <!-- Add New Card -->
            <v-col cols="12" sm="6" md="4" lg="3">
                <v-card @click="startAddCategory"
                    class="premium-glass-card d-flex flex-column align-center justify-center h-100 cursor-pointer border-dashed group"
                    style="border-width: 2px !important; min-height: 258px; background: rgba(var(--v-theme-primary), 0.05); border-color: rgba(var(--v-theme-primary), 0.3) !important;"
                    rounded="xl">
                    <v-avatar color="primary" size="64" class="mb-4 elevation-8 group-on-hover-scale"
                        style="box-shadow: 0 0 20px rgba(var(--v-theme-primary), 0.3)">
                        <Plus :size="36" color="white" stroke-width="3" />
                    </v-avatar>
                    <span class="text-h6 font-weight-black text-primary">New Category</span>
                    <span class="text-caption font-weight-bold opacity-60">Create a root folder</span>
                </v-card>
            </v-col>

            <!-- Categories -->
            <v-col v-for="cat in categoriesStore.rootCategories" :key="cat.id" cols="12" sm="6" md="4" lg="3">
                <v-card class="premium-glass-card h-100 d-flex flex-column overflow-hidden border-thin elevation-2"
                    rounded="xl">
                    <div class="pa-5 d-flex align-start relative-pos z-10">
                        <div class="category-icon-container me-4" :style="{ '--icon-color': cat.color || 'primary' }">
                            <span class="text-h4 relative-pos z-2">{{ cat.icon || '🏷️' }}</span>
                            <div class="icon-gradient-bg"></div>
                        </div>
                        <div class="flex-grow-1 min-width-0">
                            <div class="text-h6 font-weight-black line-height-1 mb-1 truncate">{{ cat.name }}</div>
                            <div class="d-flex align-center ga-1">
                                <Activity :size="10"
                                    :class="cat.type === 'expense' ? 'text-error' : (cat.type === 'income' ? 'text-success' : 'text-info')" />
                                <span class="text-tiny font-weight-black text-uppercase opacity-50">{{ cat.type
                                    }}</span>
                            </div>
                        </div>
                        <div class="d-flex flex-column ga-1 mt-n1 me-n1">
                            <v-btn icon variant="text" size="x-small" color="medium-emphasis"
                                class="bg-surface elevation-1" @click.stop="editCategory(cat)">
                                <Pencil :size="14" />
                            </v-btn>
                        </div>
                    </div>

                    <!-- Subcategories -->
                    <div class="px-3 pb-3 flex-grow-1 d-flex flex-column">
                        <div class="bg-surface-lighten-1 rounded-lg pa-2 flex-grow-1">
                            <div v-if="categoriesStore.getChildren(cat.id).length > 0" class="d-flex flex-column ga-1">
                                <div v-for="child in categoriesStore.getChildren(cat.id)" :key="child.id"
                                    class="subcategory-pill pa-2 px-3 group cursor-pointer rounded-lg relative-pos overflow-hidden transition-all border-thin"
                                    :style="{ '--child-color': cat.color || 'primary' }"
                                    @click.stop="editCategory(child)">
                                    <div class="d-flex justify-space-between align-center relative-pos z-2">
                                        <div class="d-flex align-center ga-2">
                                            <span class="text-body-2">{{ child.icon }}</span>
                                            <span class="text-caption font-weight-black truncate">{{ child.name
                                                }}</span>
                                        </div>
                                        <div
                                            class="d-flex ga-1 opacity-0 group-hover-opacity-100 transition-all duration-200">
                                            <v-btn variant="flat" color="error" size="x-small"
                                                class="rounded-lg action-btn elevation-2"
                                                @click.stop="startDeleteCategory(child)">
                                                <Trash2 :size="12" />
                                            </v-btn>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div v-else
                                class="d-flex flex-column align-center justify-center py-6 opacity-20 border-dashed rounded-lg h-100"
                                style="border-width: 1px !important;">
                                <Layers :size="24" class="mb-1" />
                                <span class="text-tiny font-weight-bold">Empty Folder</span>
                            </div>
                        </div>
                    </div>

                    <!-- Bottom Toolbar -->
                    <v-divider class="opacity-5" />
                    <div class="px-4 py-3 d-flex align-center justify-space-between">
                        <v-btn variant="tonal" color="primary" class="rounded-lg font-weight-black text-none"
                            height="32" @click.stop="startAddSubCategory(cat)">
                            <template v-slot:prepend>
                                <Plus :size="14" />
                            </template>
                            Add Sub
                        </v-btn>
                        <v-btn variant="text" color="error" class="rounded-lg action-large-btn"
                            @click.stop="startDeleteCategory(cat)">
                            <Trash2 :size="18" />
                            <v-tooltip activator="parent" location="top">Delete Parent</v-tooltip>
                        </v-btn>
                    </div>

                    <!-- Subtle background icon -->
                    <div class="card-bg-icon-standard">
                        <Folder :size="100" />
                    </div>
                </v-card>
            </v-col>
        </v-row>

        <!-- Add/Edit Category Modal -->
        <v-dialog v-model="showCategoryModal" max-width="500px" persistent>
            <v-card class="premium-glass-card no-hover overflow-hidden" rounded="xl" elevation="24">
                <v-card-title class="pa-5 border-b d-flex align-center bg-surface">
                    <div class="d-flex align-center ga-3 flex-grow-1">
                        <v-avatar :style="{ background: categoryForm.color + '20' }" rounded="lg" size="48"
                            class="elevation-2 border">
                            <span class="text-h4">{{ categoryForm.icon || '🏷️' }}</span>
                        </v-avatar>
                        <div>
                            <div class="text-overline font-weight-black opacity-50 line-height-1 mb-1">
                                {{ isEditingCategory ? 'Update' : 'New' }} Category
                            </div>
                            <div class="text-h6 font-weight-black line-height-1 truncate" style="max-width: 250px;">
                                {{ previewName }}
                            </div>
                        </div>
                    </div>
                    <v-btn icon variant="text" size="small" @click="showCategoryModal = false" color="medium-emphasis">
                        <X :size="20" />
                    </v-btn>
                </v-card-title>

                <v-card-text class="pa-5 overflow-y-auto custom-scrollbar" style="max-height: 70vh;">
                    <v-form @submit.prevent="saveCategory">
                        <div class="d-flex flex-column ga-4">
                            <!-- Basic Identity Section -->
                            <v-card variant="flat" rounded="xl" class="bg-background border-thin pa-4">
                                <v-row dense>
                                    <v-col cols="3">
                                        <v-text-field v-model="categoryForm.icon" label="Icon" variant="underlined"
                                            placeholder="Emoji" hide-details
                                            class="font-weight-black text-h5 centered-input" density="compact" />
                                    </v-col>
                                    <v-col cols="9">
                                        <v-text-field v-model="categoryForm.name" label="Category Name"
                                            variant="underlined" required placeholder="e.g. Subscriptions" hide-details
                                            class="font-weight-black text-h6" density="compact" autofocus />
                                    </v-col>
                                </v-row>
                            </v-card>

                            <!-- Configuration Section -->
                            <v-card variant="flat" rounded="xl" class="bg-background border-thin pa-4">
                                <div class="d-flex flex-column ga-4">
                                    <v-select v-model="categoryForm.parent_id" label="Parent Category"
                                        variant="solo-filled" flat rounded="lg" hide-details density="compact"
                                        :items="parentOptions" item-title="title" item-value="value"
                                        class="font-weight-bold" bg-color="surface">
                                        <template v-slot:prepend-inner>
                                            <Folder :size="16" class="text-primary mr-1 opacity-70" />
                                        </template>
                                    </v-select>

                                    <v-select v-model="categoryForm.type" label="Financial Type" variant="solo-filled"
                                        flat rounded="lg" hide-details density="compact" :items="[
                                            { title: '🔴 Expense', value: 'expense' },
                                            { title: '🟢 Income', value: 'income' },
                                            { title: '🔄 Transfer', value: 'transfer' }
                                        ]" class="font-weight-bold" bg-color="surface">
                                        <template v-slot:prepend-inner>
                                            <Activity :size="16" class="text-primary mr-1 opacity-70" />
                                        </template>
                                    </v-select>
                                </div>
                            </v-card>

                            <!-- Theme Color Section -->
                            <v-card variant="flat" rounded="xl" class="bg-background border-thin pa-4">
                                <div
                                    class="text-tiny font-weight-black opacity-50 text-uppercase letter-spacing-1 mb-3">
                                    Theme
                                    Color</div>
                                <div class="d-flex flex-wrap ga-2 align-center">
                                    <v-btn v-for="c in colorPresets" :key="c" :color="c" icon size="x-small"
                                        @click="categoryForm.color = c" :elevation="categoryForm.color === c ? 4 : 0"
                                        :class="{ 'border-2 border-white': categoryForm.color === c }"
                                        style="width: 24px; height: 24px;" />
                                    <v-divider vertical class="mx-1" height="20" />
                                    <div class="relative-pos">
                                        <input type="color" v-model="categoryForm.color" class="custom-color-input" />
                                    </div>
                                </div>
                            </v-card>
                        </div>
                    </v-form>
                </v-card-text>

                <v-card-actions class="pa-5 bg-surface border-t">
                    <v-spacer />
                    <v-btn variant="text" @click="showCategoryModal = false" class="text-none px-6 font-weight-bold"
                        rounded="pill">Cancel</v-btn>
                    <v-btn color="primary" rounded="pill" class="text-none px-8 font-weight-black elevation-8"
                        @click="saveCategory" height="44">
                        {{ isEditingCategory ? 'Save Changes' : 'Create Category' }}
                    </v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>

        <!-- Delete Confirmation Modal -->
        <v-dialog v-model="showDeleteCategoryConfirm" max-width="450px" persistent>
            <v-card class="premium-glass-card no-hover text-center pa-8" rounded="xl" elevation="24">
                <v-avatar color="error" variant="tonal" size="72" class="mb-6 mx-auto elevation-2">
                    <AlertCircle :size="40" />
                </v-avatar>
                <h3 class="text-h5 font-weight-black mb-2">Delete Category?</h3>
                <p class="text-subtitle-2 font-weight-medium opacity-60 mb-8 px-4">
                    Existing transactions will become <strong>uncategorized</strong>. This action is permanent and
                    affects your
                    financial
                    history.
                </p>
                <div class="d-flex ga-3 justify-center">
                    <v-btn variant="text" rounded="pill" class="text-none font-weight-bold px-6" height="44"
                        @click="showDeleteCategoryConfirm = false">No, Keep It</v-btn>
                    <v-btn color="error" rounded="pill" class="text-none font-weight-black px-8 elevation-4" height="44"
                        @click="confirmDeleteCategory">Yes, Delete</v-btn>
                </div>
            </v-card>
        </v-dialog>

        <!-- Delete Restricted Modal -->
        <v-dialog v-model="showDeleteRestrictedModal" max-width="450px" persistent>
            <v-card class="premium-glass-card no-hover text-center pa-8" rounded="xl" elevation="24">
                <v-avatar color="warning" variant="tonal" size="72" class="mb-6 mx-auto elevation-2">
                    <AlertCircle :size="40" />
                </v-avatar>
                <h3 class="text-h5 font-weight-black mb-2">Notice</h3>
                <p class="text-subtitle-2 font-weight-medium opacity-60 mb-8 px-4">
                    This category contains <strong>active sub-categories</strong>. Please delete or move those first
                    before
                    removing the parent folder.
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
    Download, Upload, AlertCircle, X,
    BarChart3, TrendingDown, TrendingUp, Repeat, Activity
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
    width: 24px;
    height: 24px;
    padding: 0;
    border: 1px solid rgba(var(--v-border-color), 0.2);
    border-radius: 50%;
    cursor: pointer;
    background: transparent;
    overflow: hidden;
}

.custom-color-input::-webkit-color-swatch-wrapper {
    padding: 0;
}

.custom-color-input::-webkit-color-swatch {
    border: none;
    border-radius: 50%;
}

.card-bg-icon-standard {
    position: absolute;
    bottom: -1rem;
    right: -1rem;
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

.category-icon-container {
    position: relative;
    width: 52px;
    height: 52px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 14px;
    border: 1px solid rgba(var(--v-border-color), 0.1);
    background: rgba(var(--v-theme-surface), 0.5);
    overflow: hidden;
    transition: all 0.3s ease;
}

.icon-gradient-bg {
    position: absolute;
    top: 50%;
    left: 50%;
    width: 140%;
    height: 140%;
    transform: translate(-50%, -50%);
    background: radial-gradient(circle, var(--icon-color) 0%, transparent 70%);
    opacity: 0.1;
    z-index: 1;
    transition: all 0.3s ease;
}

.premium-glass-card:hover .category-icon-container {
    transform: translateY(-2px);
    border-color: var(--icon-color);
}

.subcategory-pill {
    background: rgba(var(--v-theme-surface), 0.5);
    border-left: 3px solid transparent;
    transition: all 0.2s ease;
}

.subcategory-pill:hover {
    border-left-color: var(--child-color);
    transform: translateX(4px);
    background: rgb(var(--v-theme-surface));
}

.action-btn {
    min-width: 24px !important;
    width: 24px !important;
    height: 24px !important;
    padding: 0 !important;
}

.action-large-btn {
    min-width: 36px !important;
    width: 36px !important;
    height: 36px !important;
    padding: 0 !important;
    opacity: 0.4;
}

.action-large-btn:hover {
    opacity: 1;
}

.centered-input :deep(input) {
    text-align: center;
    font-size: 1.5rem;
}

.ga-y-6 {
    row-gap: 1.5rem;
}

.text-tiny {
    font-size: 0.7rem;
    letter-spacing: 0.05em;
}

.letter-spacing-2 {
    letter-spacing: 2px !important;
}

.truncate {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
</style>
