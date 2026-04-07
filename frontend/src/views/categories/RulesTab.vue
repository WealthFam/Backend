<template>
    <v-container fluid class="pa-0 animate-in relative-pos z-10">
        <!-- Control Bar -->
        <v-card class="premium-glass-card pa-3 mb-8 no-hover border-thin elevation-2" rounded="xl">
            <v-row align="center" dense>
                <v-col cols="12" sm="4">
                    <v-text-field v-model="rulesStore.searchQuery" placeholder="Search rules..." hide-details
                        density="compact" variant="solo-filled" flat rounded="lg" class="font-weight-bold"
                        bg-color="surface">
                        <template v-slot:prepend-inner>
                            <Search :size="18" class="text-primary mr-2 opacity-70" />
                        </template>
                    </v-text-field>
                </v-col>

                <v-spacer />

                <v-col cols="12" sm="auto" class="d-flex align-center ga-3">
                    <div class="glass-card border rounded-pill d-flex align-center pa-1 shadow-sm"
                        style="background: rgba(var(--v-theme-surface), 0.5)">
                        <v-btn variant="text" size="small" rounded="pill" color="primary"
                            class="text-none font-weight-black px-4" @click="rulesStore.applyAllRules"
                            :loading="rulesStore.loading">
                            <template v-slot:prepend>
                                <Zap :size="14" />
                            </template>
                            Bulk Apply
                            <v-tooltip activator="parent" location="top">Run all rules against transaction history</v-tooltip>
                        </v-btn>
                        <v-divider vertical class="mx-1 my-1 opacity-10" />
                        <v-btn variant="text" size="small" rounded="pill" color="primary"
                            class="text-none font-weight-black px-4" @click="rulesStore.exportRules">
                            <template v-slot:prepend>
                                <Download :size="14" />
                            </template>
                            Export
                            <v-tooltip activator="parent" location="top">Export rules to JSON</v-tooltip>
                        </v-btn>
                        <v-divider vertical class="mx-1 my-1 opacity-10" />
                        <v-btn variant="text" size="small" rounded="pill" color="primary"
                            class="text-none font-weight-black px-4" @click="ruleFileInput?.click()">
                            <template v-slot:prepend>
                                <Upload :size="14" />
                            </template>
                            Import
                            <v-tooltip activator="parent" location="top">Import rules from JSON</v-tooltip>
                            <input type="file" ref="ruleFileInput" class="d-none" accept=".json"
                                @change="handleRuleImport" />
                        </v-btn>
                    </div>
                </v-col>
            </v-row>
        </v-card>

        <!-- Suggestions Section -->
        <v-expand-transition>
            <div v-if="rulesStore.suggestions.length > 0" class="mb-10">
                <div class="d-flex align-center ga-3 mb-6">
                    <v-avatar color="secondary" variant="tonal" size="48" class="elevation-2 border">
                        <Sparkles :size="24" class="text-secondary" />
                    </v-avatar>
                    <div>
                        <div class="d-flex align-center ga-2 mb-1">
                            <h2 class="text-h6 font-weight-black line-height-1">Smart Suggestions</h2>
                            <v-chip size="x-small" color="secondary" variant="flat"
                                class="font-weight-black letter-spacing-1 elevation-1">
                                {{ rulesStore.suggestions.length }}
                            </v-chip>
                        </div>
                        <p class="text-caption font-weight-bold opacity-60">Automated classification based on activity
                        </p>
                    </div>
                </div>

                <v-row class="ga-y-4">
                    <v-col v-for="s in rulesStore.suggestions" :key="s.name" cols="12" md="4">
                        <v-card
                            class="premium-glass-card pa-5 overflow-hidden border-thin elevation-2 h-100 d-flex flex-column"
                            rounded="xl">
                            <div class="relative-pos z-10 flex-grow-1">
                                <div class="d-flex justify-space-between align-start mb-3">
                                    <div class="min-w-0 flex-grow-1">
                                        <div class="d-flex align-center ga-2 mb-1">
                                            <div class="text-h6 font-weight-black truncate" :title="s.name">{{ s.name }}
                                            </div>
                                            <v-chip v-if="s.count" size="x-small" color="secondary" variant="tonal"
                                                class="px-2 font-weight-black border">
                                                {{ s.count }}x
                                            </v-chip>
                                        </div>
                                        <div v-if="s.reason"
                                            class="text-tiny font-weight-black opacity-40 mb-2 truncate"
                                            :title="s.reason">
                                            {{ s.reason }}
                                        </div>
                                    </div>
                                    <div class="d-flex ga-1 ms-2">
                                        <v-btn variant="tonal" size="x-small" color="medium-emphasis"
                                            class="bg-surface border-thin" @click="rulesStore.ignoreSuggestion(s)">
                                            <X :size="14" />
                                        </v-btn>
                                        <v-btn color="primary" variant="flat" size="x-small" class="elevation-2"
                                            @click="openSuggestionModal(s)">
                                            <Check :size="14" />
                                        </v-btn>
                                    </div>
                                </div>
                                <div class="text-caption font-weight-medium opacity-60 mb-4 italic truncate">
                                    matches "{{ s.keywords.join(', ') }}"
                                </div>
                                <div class="d-flex align-center ga-2">
                                    <v-chip color="primary" variant="tonal" size="small"
                                        class="font-weight-black letter-spacing-1 elevation-1" border label>
                                        {{ categoriesStore.getCategoryDisplay(s.category) }}
                                    </v-chip>
                                    <v-spacer />
                                    <div v-if="s.confidence_level" class="d-flex align-center ga-1 pr-1">
                                        <Zap :size="12"
                                            :class="['High', 'Very High'].includes(s.confidence_level) ? 'text-success' : 'text-warning'" />
                                        <span class="text-tiny font-weight-black opacity-60">{{ s.confidence_level
                                            }}</span>
                                    </div>
                                </div>
                            </div>
                            <Sparkles class="card-bg-icon-standard" style="opacity: 0.05" />
                        </v-card>
                    </v-col>
                </v-row>
            </div>
        </v-expand-transition>

        <!-- Active Rules Grid -->
        <v-divider class="mb-10 opacity-5" />

        <div class="d-flex align-center ga-3 mb-6 px-1">
            <v-avatar color="primary" variant="tonal" size="48" class="elevation-2 border">
                <FileText :size="24" class="text-primary" />
            </v-avatar>
            <div>
                <div class="d-flex align-center ga-2 mb-1">
                    <h2 class="text-h6 font-weight-black line-height-1">Active Rules</h2>
                    <v-chip size="x-small" color="primary" variant="flat"
                        class="font-weight-black letter-spacing-1 elevation-1">
                        {{ rulesStore.rules.length }}
                    </v-chip>
                </div>
                <p class="text-caption font-weight-bold opacity-60">Custom classification and categorization logic</p>
            </div>
        </div>

        <v-row v-if="rulesStore.filteredRules.length === 0" class="justify-center py-16">
            <v-col cols="12" sm="8" md="6" class="text-center">
                <v-avatar size="96" color="surface-variant" variant="tonal" class="mb-6 elevation-2 border">
                    <FileText :size="48" class="opacity-20" />
                </v-avatar>
                <h3 class="text-h5 font-weight-black mb-2">No Rules Found</h3>
                <p class="text-subtitle-1 opacity-60 mb-8 font-weight-medium mx-auto" style="max-width: 400px">
                    {{ rulesStore.emptyRulesMsg }}
                </p>
                <v-btn v-if="!rulesStore.searchQuery" color="primary" rounded="pill" size="large"
                    class="text-none px-10 elevation-8 font-weight-black" @click="openAddRuleModal">
                    Create First Rule
                </v-btn>
            </v-col>
        </v-row>

        <!-- Rules Grid -->
        <v-row v-else class="pb-16 ga-y-6">
            <!-- Add New Rule Card -->
            <v-col cols="12" sm="6" lg="4">
                <v-card
                    class="premium-glass-card group h-100 d-flex flex-column align-center justify-center border-dashed group"
                    rounded="xl"
                    style="min-height: 240px; cursor: pointer; border-width: 2px !important; background: rgba(var(--v-theme-primary), 0.05); border-color: rgba(var(--v-theme-primary), 0.3) !important;"
                    @click="openAddRuleModal">
                    <v-avatar color="primary" size="64" class="mb-4 elevation-8 group-on-hover-scale"
                        style="box-shadow: 0 0 20px rgba(var(--v-theme-primary), 0.3)">
                        <Plus :size="36" color="white" stroke-width="3" />
                    </v-avatar>
                    <div class="text-h6 font-weight-black text-primary">Add New Rule</div>
                    <div class="text-caption font-weight-bold opacity-60">Create custom classification</div>
                </v-card>
            </v-col>

            <v-col v-for="rule in rulesStore.filteredRules" :key="rule.id" cols="12" sm="6" lg="4">
                <v-card class="premium-glass-card h-100 d-flex flex-column overflow-hidden border-thin elevation-2"
                    rounded="xl">
                    <div class="pa-5 flex-grow-1 relative-pos z-10">
                        <div class="d-flex justify-space-between align-start mb-6">
                            <div class="d-flex align-center ga-3 min-w-0">
                                <v-avatar color="primary" variant="tonal" rounded="lg" size="48"
                                    class="elevation-1 border">
                                    <FileText :size="24" />
                                </v-avatar>
                                <div class="min-w-0">
                                    <div class="text-h6 font-weight-black truncate mb-1" :title="rule.name">{{ rule.name
                                    }}
                                    </div>
                                    <div v-if="rule.exclude_from_reports" class="d-flex align-center ga-1 pr-1">
                                        <EyeOff :size="10" class="text-error" />
                                        <span
                                            class="text-tiny font-weight-black text-uppercase text-error">Hidden</span>
                                    </div>
                                    <span v-else class="text-tiny font-weight-black opacity-50 text-uppercase">
                                        {{ rule.keywords.length }} Keywords
                                    </span>
                                </div>
                            </div>

                            <div class="text-right shrink-0 ml-2">
                                <span
                                    class="text-tiny font-weight-black opacity-40 text-uppercase d-block mb-1">Category</span>
                                <v-chip density="compact" size="small" variant="flat" color="surface"
                                    class="font-weight-black border elevation-1" label>
                                    {{ categoriesStore.getCategoryDisplay(rule.category) }}
                                </v-chip>
                                <v-chip v-if="rule.is_transfer" density="compact" size="small" variant="flat"
                                    color="secondary" class="font-weight-black border elevation-1 ml-1" label>
                                    <Shuffle :size="10" class="mr-1" /> Transfer
                                </v-chip>
                            </div>
                        </div>

                        <!-- Keywords Box -->
                        <div class="bg-surface-lighten-1 rounded-lg pa-4 border-thin border-dashed">
                            <div class="d-flex flex-wrap ga-2">
                                <v-chip v-for="(k, idx) in rule.keywords.slice(0, 6)" :key="idx" size="x-small"
                                    variant="flat" class="font-mono font-weight-black bg-surface elevation-1 border">
                                    {{ k }}
                                </v-chip>
                                <v-chip v-if="rule.keywords.length > 6" size="x-small" variant="text"
                                    class="text-primary font-weight-black">
                                    +{{ rule.keywords.length - 6 }} more
                                </v-chip>
                                <div v-if="rule.keywords.length === 0"
                                    class="text-caption italic opacity-30 w-100 text-center py-2">No keywords</div>
                            </div>
                        </div>
                    </div>

                    <v-divider class="opacity-5" />

                    <!-- Bottom Actions -->
                    <div class="px-4 py-3 d-flex align-center justify-space-between bg-transparent">
                        <div class="d-flex ga-1">
                            <v-btn variant="tonal" color="primary" class="rounded-lg font-weight-black text-none"
                                height="32" @click="handleApplyRuleRetrospectively(rule.id)">
                                <template v-slot:prepend>
                                    <Zap :size="14" />
                                </template>
                                Apply
                                <v-tooltip activator="parent" location="top">Apply this rule to history</v-tooltip>
                            </v-btn>
                            <v-btn variant="text" size="small" color="medium-emphasis" class="rounded-lg border-thin"
                                style="min-width: 32px; width: 32px;" @click="updatePriority(rule, 1)">
                                <ArrowUp :size="14" />
                                <v-tooltip activator="parent" location="top">Increase Priority</v-tooltip>
                            </v-btn>
                            <v-btn variant="text" size="small" color="medium-emphasis" class="rounded-lg border-thin"
                                style="min-width: 32px; width: 32px;" @click="updatePriority(rule, -1)">
                                <ArrowDown :size="14" />
                                <v-tooltip activator="parent" location="top">Decrease Priority</v-tooltip>
                            </v-btn>
                        </div>
                        <div class="d-flex ga-1">
                            <v-btn icon variant="text" size="small" color="primary"
                                class="rounded-lg border-thin" @click="duplicateRule(rule)">
                                <Copy :size="16" />
                                <v-tooltip activator="parent" location="top">Duplicate Rule</v-tooltip>
                            </v-btn>
                            <v-btn icon variant="text" size="small" color="medium-emphasis"
                                class="rounded-lg border-thin" @click="openEditRuleModal(rule)">
                                <Pencil :size="16" />
                                <v-tooltip activator="parent" location="top">Edit Rule</v-tooltip>
                            </v-btn>
                            <v-btn icon variant="text" size="small" color="error" class="rounded-lg border-thin"
                                @click="deleteRule(rule.id)">
                                <Trash2 :size="16" />
                                <v-tooltip activator="parent" location="top">Delete Rule</v-tooltip>
                            </v-btn>
                        </div>
                    </div>

                    <!-- Subtle background icon -->
                    <div class="card-bg-icon-standard">
                        <Filter :size="80" />
                    </div>
                </v-card>
            </v-col>
        </v-row>

        <!-- Add/Edit Rule Modal -->
        <v-dialog v-model="showRuleModal" max-width="500px" persistent>
            <v-card class="premium-glass-card no-hover overflow-hidden" rounded="xl" elevation="24">
                <v-card-title class="pa-5 border-b d-flex align-center bg-surface">
                    <div class="d-flex align-center ga-3 flex-grow-1">
                        <v-avatar color="primary" variant="tonal" rounded="lg" size="48" class="elevation-2 border">
                            <FileText :size="24" />
                        </v-avatar>
                        <div>
                            <div class="text-overline font-weight-black opacity-50 line-height-1 mb-1">
                                {{ isEditingRule ? 'Update' : 'New' }} Intelligence Rule
                            </div>
                            <div class="text-h6 font-weight-black line-height-1 truncate" style="max-width: 250px;">
                                {{ newRule.name || 'Set Classification Logic' }}
                            </div>
                        </div>
                    </div>
                    <v-btn icon variant="text" size="small" @click="showRuleModal = false" color="medium-emphasis">
                        <X :size="20" />
                    </v-btn>
                </v-card-title>

                <v-card-text class="pa-5 overflow-y-auto custom-scrollbar" style="max-height: 70vh;">
                    <v-form @submit.prevent="saveRule">
                        <div class="d-flex flex-column ga-4">
                            <!-- Basic Identity Section -->
                            <v-card variant="flat" rounded="xl" class="bg-background border-thin pa-4">
                                <v-text-field v-model="newRule.name" label="Rule Identifier" variant="underlined"
                                    placeholder="e.g. Swiggy Orders" required hide-details
                                    class="font-weight-black text-h6" density="compact" autofocus />
                            </v-card>

                            <!-- Configuration Section -->
                            <v-card variant="flat" rounded="xl" class="bg-background border-thin pa-4">
                                <div class="d-flex flex-column ga-4">
                                    <v-autocomplete v-model="newRule.category" label="Target Category" variant="solo-filled"
                                        flat rounded="lg" hide-details density="compact"
                                        :items="categoriesStore.categories.map(c => ({ title: `${c.icon || '🏷️'} ${c.name}`, value: c.name }))"
                                        placeholder="Select Category" :required="!newRule.is_transfer" class="font-weight-bold"
                                        bg-color="surface">
                                        <template v-slot:prepend-inner>
                                            <Folder :size="16" class="text-primary mr-1 opacity-70" />
                                        </template>
                                    </v-autocomplete>

                                    <v-combobox v-model="newRule.keywords" label="Trigger Keywords" multiple chips
                                        closable-chips variant="solo-filled" flat rounded="lg" hide-details
                                        density="compact" placeholder="Press enter to add keywords"
                                        class="font-weight-bold" bg-color="surface">
                                        <template v-slot:prepend-inner>
                                            <Zap :size="16" class="text-primary mr-1 opacity-70" />
                                        </template>
                                        <template v-slot:selection="{ item }">
                                            <v-chip size="small" color="primary" variant="flat"
                                                class="font-mono font-weight-black elevation-1">
                                                {{ item.raw }}
                                            </v-chip>
                                        </template>
                                    </v-combobox>

                                    <div
                                        class="text-tiny font-weight-black opacity-50 text-uppercase letter-spacing-1 mt-n2 px-1">
                                        Matches any description containing these terms.
                                    </div>
                                </div>
                            </v-card>
                            <!-- Advanced Logic Section -->
                            <v-card variant="flat" rounded="xl" class="bg-background border-thin pa-4">
                                <div class="d-flex flex-column ga-4">
                                    <div class="d-flex align-center justify-space-between">
                                        <div class="text-subtitle-2 font-weight-black text-primary d-flex align-center ga-2">
                                            Test Precision
                                            <v-chip size="x-small" color="primary" variant="tonal" class="font-weight-black">ALPHA</v-chip>
                                        </div>
                                        <v-btn variant="tonal" size="small" rounded="pill" color="primary"
                                            class="text-none font-weight-black" @click="testCurrentLogic"
                                            :disabled="!newRule.keywords.length">
                                            <template v-slot:prepend>
                                                <Zap :size="14" />
                                            </template>
                                            Test Logic
                                        </v-btn>
                                    </div>

                                    <v-expand-transition>
                                        <div v-if="testingLogic" class="py-2">
                                            <v-progress-linear indeterminate color="primary" height="2" rounded />
                                        </div>
                                        <div v-else-if="testResultCount !== null" class="bg-surface pa-3 rounded-lg border-thin">
                                            <div class="d-flex align-center justify-space-between mb-2">
                                                <span class="text-tiny font-weight-black opacity-50 uppercase">Match Results</span>
                                                <v-chip size="x-small" :color="testResultCount > 0 ? 'success' : 'warning'" variant="flat">
                                                    {{ testResultCount }} matches
                                                </v-chip>
                                            </div>
                                            <div v-if="testResultCount > 0" class="text-tiny font-weight-medium opacity-70">
                                                This rule will categorize {{ testResultCount }} transactions.
                                            </div>
                                            <div v-else class="text-tiny font-weight-medium text-warning">
                                                No transactions found with these keywords.
                                            </div>
                                        </div>
                                    </v-expand-transition>

                                    <v-divider class="my-1 opacity-5" />

                                    <div class="d-flex align-center justify-space-between">
                                        <div class="text-subtitle-2 font-weight-black">Is Transfer?</div>
                                        <v-switch v-model="newRule.is_transfer" color="secondary" inset hide-details
                                            density="compact" />
                                    </div>

                                    <v-expand-transition>
                                        <div v-if="newRule.is_transfer">
                                            <v-autocomplete v-model="newRule.to_account_id" label="Destination Account"
                                                variant="solo-filled" flat rounded="lg" hide-details density="compact"
                                                :items="financeStore.accounts.map(a => ({ title: a.name, value: a.id }))"
                                                placeholder="Select Destination" required class="font-weight-bold"
                                                bg-color="surface">
                                                <template v-slot:prepend-inner>
                                                    <CreditCard :size="16" class="text-secondary mr-1 opacity-70" />
                                                </template>
                                            </v-autocomplete>
                                        </div>
                                    </v-expand-transition>

                                    <div class="d-flex align-center ga-3">
                                        <div class="text-subtitle-2 font-weight-black shrink-0">Priority</div>
                                        <v-slider v-model="newRule.priority" :min="0" :max="100" :step="1" hide-details
                                            color="primary" class="flex-grow-1">
                                            <template v-slot:append>
                                                <div class="text-caption font-weight-black bg-surface px-2 py-1 rounded border-thin"
                                                    style="min-width: 40px; text-align: center;">
                                                    {{ newRule.priority }}
                                                </div>
                                            </template>
                                        </v-slider>
                                    </div>
                                </div>
                            </v-card>

                            <!-- Reporting Options -->
                            <v-card variant="flat" rounded="xl" class="bg-background border-thin pa-1">
                                <v-switch v-model="newRule.exclude_from_reports" color="error" inset hide-details
                                    class="px-4">
                                    <template v-slot:label>
                                        <div class="ml-2 py-2">
                                            <div class="text-subtitle-2 font-weight-black line-height-1 mb-1">Hide from
                                                reports</div>
                                            <div class="text-tiny font-weight-bold opacity-60">Exclude from dashboard
                                                analytics and totals.</div>
                                        </div>
                                    </template>
                                </v-switch>
                            </v-card>
                        </div>
                    </v-form>
                </v-card-text>

                <v-card-actions class="pa-5 bg-surface border-t">
                    <v-spacer />
                    <v-btn variant="text" @click="showRuleModal = false" class="text-none px-6 font-weight-bold"
                        rounded="pill">Cancel</v-btn>
                    <v-btn color="primary" rounded="pill" class="text-none px-8 font-weight-black elevation-8"
                        @click="saveRule" height="44">
                        Save Intelligence
                    </v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>

        <!-- Confirmation Dialogs -->
        <!-- Delete Rule -->
        <v-dialog v-model="showRuleDeleteConfirm" max-width="450px" persistent>
            <v-card class="premium-glass-card no-hover text-center pa-8" rounded="xl" elevation="24">
                <v-avatar color="error" variant="tonal" size="72" class="mb-6 mx-auto elevation-2">
                    <Trash2 :size="40" />
                </v-avatar>
                <h3 class="text-h5 font-weight-black mb-2">Delete Classification Rule?</h3>
                <p class="text-subtitle-2 font-weight-medium opacity-60 mb-8 px-4">
                    Future transactions matched by this rule will become <strong>uncategorized</strong>.
                </p>
                <div class="d-flex ga-3 justify-center">
                    <v-btn variant="text" rounded="pill" class="text-none font-weight-bold px-6" height="44"
                        @click="showRuleDeleteConfirm = false">Cancel</v-btn>
                    <v-btn color="error" rounded="pill" class="text-none font-weight-black px-8 elevation-4" height="44"
                        @click="confirmDeleteRule">Yes, Delete</v-btn>
                </div>
            </v-card>
        </v-dialog>

        <!-- Exclude confirmation -->
        <v-dialog v-model="showExcludeConfirm" max-width="450px" persistent>
            <v-card class="premium-glass-card no-hover text-center pa-8" rounded="xl" elevation="24">
                <v-avatar color="warning" variant="tonal" size="72" class="mb-6 mx-auto elevation-2">
                    <EyeOff :size="40" />
                </v-avatar>
                <h3 class="text-h5 font-weight-black mb-2">Invisible in Reports?</h3>
                <p class="text-subtitle-2 font-weight-medium opacity-60 mb-8 px-4">
                    Transactions matching this rule will be <strong>hidden</strong> from monthly totals and charts.
                </p>
                <div class="d-flex ga-3 justify-center">
                    <v-btn variant="text" rounded="pill" class="text-none font-weight-bold px-6" height="44"
                        @click="showExcludeConfirm = false">Back</v-btn>
                    <v-btn color="primary" rounded="pill" class="text-none font-weight-black px-8 elevation-4"
                        height="44" @click="confirmSaveRule">Confirm & Save</v-btn>
                </div>
            </v-card>
        </v-dialog>

        <!-- Apply Retro -->
        <v-dialog v-model="showApplyRuleConfirm" max-width="500px" persistent>
            <v-card class="premium-glass-card no-hover text-center pa-8" rounded="xl" elevation="24">
                <v-avatar color="primary" variant="tonal" size="72" class="mb-6 mx-auto elevation-2">
                    <Zap :size="40" />
                </v-avatar>
                <h3 class="text-h5 font-weight-black mb-2">Retroactive Application</h3>
                <p class="text-subtitle-2 font-weight-medium opacity-60 mb-6">
                    Scan your history and apply this logic to matching records?
                </p>

                <!-- Override Switch -->
                <v-card variant="flat" color="primary" rounded="pill"
                    class="pa-1 pr-4 border-thin bg-surface mb-6 mx-auto d-inline-flex">
                    <v-switch v-model="rulesStore.overrideExisting" color="primary" inset hide-details density="compact"
                        @update:model-value="refetchPreview">
                        <template v-slot:label>
                            <span class="text-tiny font-weight-black ml-2 text-uppercase">Override existing
                                categories</span>
                        </template>
                    </v-switch>
                </v-card>

                <v-expand-transition>
                    <div v-if="rulesStore.previewLoading" class="py-8">
                        <v-progress-circular indeterminate color="primary" size="32" />
                        <div class="mt-2 text-tiny font-weight-black opacity-60 text-uppercase">Scanning history...
                        </div>
                    </div>
                    <div v-else-if="rulesStore.matchingCount > 0" class="mb-8">
                        <div class="bg-surface-lighten-1 rounded-lg pa-4 border-thin text-left border-dashed">
                            <div class="d-flex align-center justify-space-between mb-3">
                                <span class="text-tiny font-weight-black opacity-50 text-uppercase">Preview (Latest 5 of
                                    {{
                                        rulesStore.matchingCount }})</span>
                                <v-chip size="x-small" color="primary" variant="flat"
                                    class="font-weight-black elevation-1">
                                    {{ rulesStore.matchingCount }} matches
                                </v-chip>
                            </div>
                            <div class="d-flex flex-column ga-2">
                                <div v-for="txn in rulesStore.matchingPreview" :key="txn.id"
                                    class="d-flex justify-space-between align-center border-b pb-2 last-no-border opacity-90 border-opacity-10">
                                    <div class="min-w-0 pr-2">
                                        <div class="text-caption font-weight-black truncate">{{ txn.description ||
                                            txn.recipient
                                            }}</div>
                                        <div class="text-tiny font-weight-bold opacity-50 d-flex align-center ga-1">
                                            {{ new Date(txn.date).toLocaleDateString() }}
                                            <v-chip v-if="txn.category && txn.category !== 'Uncategorized'"
                                                size="x-small" variant="text" color="primary"
                                                class="px-1 font-weight-black">
                                                · {{ txn.category }}
                                            </v-chip>
                                        </div>
                                    </div>
                                    <div class="text-caption font-weight-black shrink-0"
                                        :class="txn.amount < 0 ? 'text-error' : 'text-success'">
                                        {{ txn.amount < 0 ? '-' : '' }}₹{{ Math.abs(txn.amount).toLocaleString() }}
                                            </div>
                                    </div>
                                </div>

                                <!-- Pagination -->
                                <div v-if="rulesStore.matchingCount > rulesStore.previewLimit"
                                    class="mt-4 d-flex justify-center">
                                    <v-pagination v-model="rulesStore.previewPage"
                                        :length="Math.ceil(rulesStore.matchingCount / rulesStore.previewLimit)"
                                        :total-visible="3" density="compact" variant="flat" color="primary"
                                        active-color="primary" size="small" @update:model-value="handlePageChange" />
                                </div>
                            </div>
                        </div>
                        <div v-else-if="!rulesStore.previewLoading"
                            class="mb-8 text-center text-caption font-weight-black text-amber">
                            <AlertCircle :size="16" class="mr-1 inline-block vertical-align-middle" />
                            No matching transactions found.
                        </div>
                </v-expand-transition>

                <div class="d-flex ga-3 justify-center">
                    <v-btn variant="text" rounded="pill" class="text-none font-weight-bold px-6" height="44"
                        @click="showApplyRuleConfirm = false">Cancel</v-btn>
                    <v-btn color="primary" rounded="pill" class="text-none font-weight-black px-8 elevation-8"
                        height="44" @click="confirmApplyRule"
                        :disabled="rulesStore.matchingCount === 0 || rulesStore.previewLoading">
                        Run Logic Now
                    </v-btn>
                </div>
            </v-card>
        </v-dialog>
    </v-container>
</template>

<script setup lang="ts">
import {
    Search,
    Plus,
    Pencil,
    Trash2,
    Zap,
    Filter,
    X,
    Check,
    AlertCircle,
    EyeOff,
    Sparkles,
    FileText,
    Download,
    Upload,
    Folder,
    ArrowUp,
    ArrowDown,
    CreditCard,
    Shuffle,
    Copy
} from 'lucide-vue-next'
import { ref, onMounted } from 'vue'

import { useRulesStore, type Rule, type RuleSuggestion } from '@/stores/finance/rules'
import { useCategoriesStore } from '@/stores/finance/categories'
import { useFinanceStore } from '@/stores/finance'
import { useNotificationStore } from '@/stores/notification'
import { financeApi } from '@/api/client'

const rulesStore = useRulesStore()
const categoriesStore = useCategoriesStore()
const financeStore = useFinanceStore()
const notify = useNotificationStore()

// Local UI State (Modals)
const showRuleModal = ref(false)
const showExcludeConfirm = ref(false)
const showRuleDeleteConfirm = ref(false)
const showApplyRuleConfirm = ref(false)
const ruleToDelete = ref<string | null>(null)
const ruleToApply = ref<string | null>(null)
const isEditingRule = ref(false)
const editingRuleId = ref<string | null>(null)

const newRule = ref({
    name: '',
    category: '',
    keywords: [] as string[],
    priority: 10,
    is_transfer: false,
    to_account_id: '',
    exclude_from_reports: false
})

onMounted(() => {
    rulesStore.fetchRules()
    rulesStore.fetchSuggestions()
    if (categoriesStore.categories.length === 0) {
        categoriesStore.fetchCategories()
    }
})

function openAddRuleModal() {
    isEditingRule.value = false
    editingRuleId.value = null
    testResultCount.value = null
    newRule.value = {
        name: '',
        category: '',
        keywords: [],
        priority: 10,
        is_transfer: false,
        to_account_id: '',
        exclude_from_reports: false
    }
    showRuleModal.value = true
}

function duplicateRule(rule: Rule) {
    isEditingRule.value = false
    editingRuleId.value = null
    testResultCount.value = null
    newRule.value = {
        name: `${rule.name} (Copy)`,
        category: rule.category,
        keywords: [...rule.keywords],
        priority: rule.priority,
        is_transfer: rule.is_transfer,
        to_account_id: rule.to_account_id || '',
        exclude_from_reports: rule.exclude_from_reports || false
    }
    showRuleModal.value = true
}

function openEditRuleModal(rule: Rule) {
    isEditingRule.value = true
    editingRuleId.value = rule.id
    testResultCount.value = null
    newRule.value = {
        name: rule.name,
        category: rule.category,
        keywords: Array.isArray(rule.keywords) ? [...rule.keywords] : (rule.keywords as string).split(','),
        priority: rule.priority || 10,
        is_transfer: rule.is_transfer || false,
        to_account_id: rule.to_account_id || '',
        exclude_from_reports: rule.exclude_from_reports || false
    }
    showRuleModal.value = true
}

function openSuggestionModal(s: RuleSuggestion) {
    isEditingRule.value = false
    editingRuleId.value = null
    testResultCount.value = null
    newRule.value = {
        name: s.name,
        category: s.category,
        keywords: Array.isArray(s.keywords) ? [...s.keywords] : (s.keywords as any).split(','),
        priority: 10,
        is_transfer: false,
        to_account_id: '',
        exclude_from_reports: false
    }
    showRuleModal.value = true
}

const testingLogic = ref(false)
const testResultCount = ref<number | null>(null)

async function testCurrentLogic() {
    if (!newRule.value.keywords.length) return
    testingLogic.value = true
    try {
        const onlyUncategorized = !rulesStore.overrideExisting
        const res = await financeApi.getMatchCount(newRule.value.keywords, onlyUncategorized)
        testResultCount.value = res.data.count
    } catch (e) {
        console.error("Test failed", e)
    } finally {
        testingLogic.value = false
    }
}

async function saveRule() {
    if (!newRule.value.name || (!newRule.value.category && !newRule.value.is_transfer) || !newRule.value.keywords.length) return

    // Conflict detection
    const keywordList = Array.isArray(newRule.value.keywords) ? newRule.value.keywords : []
    const matchingRules = rulesStore.rules.filter(r => 
        r.id !== editingRuleId.value && 
        r.category !== newRule.value.category &&
        r.keywords.some((kw: string) => keywordList.includes(kw))
    )

    if (matchingRules.length > 0) {
        const confirmMsg = `Keywords overlap with rules in: ${matchingRules.map(r => r.category).join(', ')}. Continue?`
        if (!confirm(confirmMsg)) return
    }

    if (newRule.value.exclude_from_reports) {
        showExcludeConfirm.value = true
        return
    }

    await confirmSaveRule()
}

async function confirmSaveRule() {
    const keywordList = Array.isArray(newRule.value.keywords)
        ? newRule.value.keywords.map(k => k.trim())
        : (newRule.value.keywords as string).split(',').map(k => k.trim())

    const payload = {
        ...newRule.value,
        keywords: keywordList
    }

    let success = false
    if (isEditingRule.value && editingRuleId.value) {
        success = await rulesStore.updateRule(editingRuleId.value, payload)
        if (success && newRule.value.exclude_from_reports) {
            notify.success(`Rule updated! Matching transactions will be hidden from reports.`)
        }
    } else {
        success = await rulesStore.createRule(payload)
        if (success && newRule.value.exclude_from_reports) {
            notify.success(`Rule saved! Future transactions will be hidden from reports.`)
        }
    }

    if (success) {
        showRuleModal.value = false
        showExcludeConfirm.value = false
        newRule.value = {
            name: '',
            category: '',
            keywords: [],
            priority: 10,
            is_transfer: false,
            to_account_id: '',
            exclude_from_reports: false
        }
    }
}

async function updatePriority(rule: Rule, delta: number) {
    const newPriority = (rule.priority || 0) + delta
    const payload = {
        ...rule,
        priority: newPriority
    }
    await rulesStore.updateRule(rule.id, payload)
}

function deleteRule(id: string) {
    ruleToDelete.value = id
    showRuleDeleteConfirm.value = true
}

async function confirmDeleteRule() {
    if (!ruleToDelete.value) return
    const success = await rulesStore.deleteRule(ruleToDelete.value)
    if (success) {
        showRuleDeleteConfirm.value = false
        ruleToDelete.value = null
    }
}

async function handleApplyRuleRetrospectively(ruleId: string) {
    ruleToApply.value = ruleId
    const rule = rulesStore.rules.find(r => r.id === ruleId)
    if (rule) {
        showApplyRuleConfirm.value = true
        await rulesStore.fetchMatchPreview(rule.keywords)
    }
}

async function confirmApplyRule() {
    if (!ruleToApply.value) return
    const count = await rulesStore.applyRuleRetrospectively(ruleToApply.value)
    if (count !== false) {
        showApplyRuleConfirm.value = false
        ruleToApply.value = null
    }
}

async function refetchPreview() {
    if (!ruleToApply.value) return
    const rule = rulesStore.rules.find(r => r.id === ruleToApply.value)
    if (rule) {
        await rulesStore.fetchMatchPreview(rule.keywords, 1)
    }
}

async function handlePageChange(page: number) {
    if (!ruleToApply.value) return
    const rule = rulesStore.rules.find(r => r.id === ruleToApply.value)
    if (rule) {
        await rulesStore.fetchMatchPreview(rule.keywords, page)
    }
}

const ruleFileInput = ref<HTMLInputElement | null>(null)

function handleRuleImport(event: Event) {
    const input = event.target as HTMLInputElement
    if (input.files && input.files[0]) {
        rulesStore.importRules(input.files[0])
        input.value = '' // Reset
    }
}

defineExpose({
    openAddRuleModal
})
</script>

<style scoped>
.truncate {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.animate-in {
    animation: fadeIn 0.4s ease-out;
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

.line-height-1 {
    line-height: 1;
}

.last-no-border:last-child {
    border-bottom: none !important;
}

.text-tiny {
    font-size: 0.65rem !important;
    letter-spacing: 0.5px;
}

.card-bg-icon-standard {
    position: absolute;
    bottom: -1rem;
    right: -0.5rem;
    font-size: 6rem;
    opacity: 0.03;
    pointer-events: none;
    line-height: 1;
    transform: rotate(-12deg);
    transition: all 0.5s ease;
    z-index: 0;
}

.premium-glass-card:hover .card-bg-icon-standard {
    transform: rotate(0deg) scale(1.1);
    opacity: 0.06;
}

.rules-tabs :deep(.v-btn) {
    border-radius: 12px !important;
    transition: all 0.3s ease;
}

.rules-tabs :deep(.v-tab--selected) {
    background: rgba(var(--v-theme-primary), 0.1);
    color: rgb(var(--v-theme-primary)) !important;
}

.tab-item {
    font-size: 0.9rem !important;
    letter-spacing: 0.5px;
}
</style>
