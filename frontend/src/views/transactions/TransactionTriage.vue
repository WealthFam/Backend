<template>
    <div class="triage-view animate-in">
        <v-window v-model="activeTab">
            <!-- PENDING TAB -->
            <v-window-item value="pending">
                <v-alert type="info" variant="tonal" class="mb-4 rounded-xl" border="start" density="compact">
                    <template v-slot:prepend>
                        <ShieldAlert :size="20" class="mr-2 text-info" />
                    </template>
                    <strong>Review Intake</strong>: These transactions were auto-detected but require
                    categorization or confirmation before affecting your balance.
                </v-alert>

                <!-- Filters Toolbar -->
                <v-card class="premium-glass-card mb-4 pa-3 no-hover" style="border-radius: 20px !important;">
                    <v-row align="center" no-gutters class="gap-3 px-0">
                        <v-col cols="12" lg="auto" class="flex-grow-1">
                            <v-text-field :model-value="triageSearchQuery"
                                @update:model-value="emit('update:triageSearchQuery', $event)"
                                placeholder="Search description or recipient..." density="comfortable" hide-details
                                variant="outlined" rounded="lg" class="font-weight-bold" clearable autocomplete="off"
                                bg-color="surface">
                                <template v-slot:prepend-inner>
                                    <Search :size="18" class="text-primary mr-2" />
                                </template>
                            </v-text-field>
                        </v-col>

                        <v-divider vertical class="d-none d-lg-block mx-1" />

                        <v-col cols="auto">
                            <v-btn-toggle :model-value="triageSourceFilter"
                                @update:model-value="emit('update:triageSourceFilter', $event || 'ALL')"
                                density="comfortable" color="primary" variant="tonal" divided mandatory
                                class="rounded-lg border-thin">
                                <v-btn value="ALL" size="small" class="px-4">All</v-btn>
                                <v-btn value="SMS" size="small" class="px-4">SMS</v-btn>
                                <v-btn value="EMAIL" size="small" class="px-4">Email</v-btn>
                            </v-btn-toggle>
                        </v-col>

                        <v-divider vertical class="d-none d-lg-block mx-1" />

                        <v-col cols="12" md="auto" class="d-flex align-center gap-2">
                            <v-autocomplete :model-value="triageSortKey"
                                @update:model-value="emit('update:triageSortKey', $event)"
                                :items="[{ title: 'Date', value: 'date' }, { title: 'Amount', value: 'amount' }, { title: 'Description', value: 'description' }]"
                                item-title="title" item-value="value" hide-details density="comfortable"
                                variant="outlined" label="Sort" style="width: 140px" rounded="lg"
                                class="font-weight-bold" bg-color="surface"></v-autocomplete>

                            <v-tooltip :text="`Sort by ${triageSortOrder === 'asc' ? 'Descending' : 'Ascending'}`"
                                location="top" open-delay="400">
                                <template v-slot:activator="{ props }">
                                    <v-btn v-bind="props"
                                        @click="emit('update:triageSortOrder', triageSortOrder === 'asc' ? 'desc' : 'asc')"
                                        variant="tonal" size="small" height="40" width="40" color="primary"
                                        class="rounded-lg">
                                        <ArrowUpNarrowWide v-if="triageSortOrder === 'asc'" :size="18" />
                                        <ArrowDownNarrowWide v-else :size="18" />
                                    </v-btn>
                                </template>
                            </v-tooltip>
                        </v-col>
                    </v-row>
                </v-card>

                <!-- Bulk Actions -->
                <div class="d-flex align-center justify-space-between mb-4 px-2">
                    <div class="d-flex align-center gap-4">
                        <v-checkbox-btn
                            :model-value="selectedTriageIds.length === filteredTriageTransactions.length && filteredTriageTransactions.length > 0"
                            @update:model-value="toggleSelectAllTriage" color="primary" label="Select All Filtered"
                            hide-details density="compact" class="ml-1"></v-checkbox-btn>

                        <v-fade-transition>
                            <v-tooltip v-if="selectedTriageIds.length > 0"
                                :text="`Discard ${selectedTriageIds.length} selected transactions`" location="top"
                                open-delay="400">
                                <template v-slot:activator="{ props }">
                                    <v-btn v-bind="props" color="error" variant="tonal" size="small"
                                        @click="emit('update:showDiscardConfirm', true)" rounded="lg">
                                        <template v-slot:prepend>
                                            <Trash2 :size="16" />
                                        </template>
                                        Discard {{ selectedTriageIds.length }}
                                    </v-btn>
                                </template>
                            </v-tooltip>
                        </v-fade-transition>
                    </div>
                    <v-tooltip text="Refresh triage data" location="top" open-delay="400">
                        <template v-slot:activator="{ props }">
                            <v-btn v-bind="props" variant="text" size="small" @click="emit('refreshTriage')">
                                <RotateCw :size="18" />
                            </v-btn>
                        </template>
                    </v-tooltip>
                </div>

                <!-- Transactions Grid -->
                <v-row>
                    <v-col v-for="txn in filteredTriageTransactions" :key="txn.id" cols="12" md="6" lg="4">
                        <v-card class="premium-glass-card"
                            :class="{ 'is-selected': selectedTriageIds.includes(txn.id), 'is-debit': Number(txn.amount) < 0, 'is-credit': Number(txn.amount) >= 0 }">

                            <!-- Dynamic Accent Glow -->
                            <div class="card-glow-accent"></div>

                            <div class="card-modern-header px-4 pt-4 pb-2">
                                <div class="d-flex align-left gap-3 overflow-hidden">
                                    <v-checkbox-btn v-model="selectedTriageIds" :value="txn.id" color="primary"
                                        density="comfortable" hide-details class="mt-n1"></v-checkbox-btn>

                                    <div class="flex-grow-1 min-width-0">
                                        <div class="text-subtitle-2 font-weight-black text-truncate modern-header-title mb-0"
                                            :title="txn.recipient || txn.description">
                                            {{ txn.recipient || txn.description }}
                                        </div>
                                        <div class="d-flex align-center flex-wrap gap-2 text-caption opacity-60 font-weight-bold">
                                            <span>{{ formatDate(txn.date).day }}</span>
                                            <span class="opacity-50">•</span>
                                            <span>{{ txn.source }}</span>
                                            <v-chip v-if="txn.latitude" size="x-small" color="primary" variant="tonal" class="rounded-pill font-weight-bold ml-1" density="compact">
                                                <MapPin :size="10" class="mr-1" /> GPS
                                            </v-chip>
                                        </div>
                                    </div>

                                </div>
                            </div>

                            <!-- Amount Hero Section -->
                            <div class="amount-hero-section px-4 py-4 d-flex align-center justify-center">
                                <div class="text-center">
                                    <div class="modern-amount-display amount-hero-text"
                                        :class="Number(txn.amount) < 0 ? 'text-error' : 'text-success'">
                                        {{ formatAmount(Math.abs(Number(txn.amount))) }}
                                    </div>
                                    <div
                                        class="text-caption font-weight-black opacity-40 text-uppercase tracking-widest mt-n1">
                                        {{ Number(txn.amount) < 0 ? 'Debit' : 'Credit' }} </div>
                                    </div>
                                </div>

                                <!-- Card Body -->
                                <v-card-text class="flex-grow-1 px-4 py-2 d-flex flex-column gap-3">
                                    <div class="modern-metadata">
                                        <div
                                            class="d-flex align-center gap-2 text-caption font-weight-bold opacity-60 mb-2">
                                            <Zap :size="14" class="mr-1" />
                                            {{ getAccountName(txn.account_id) }}
                                        </div>

                                        <div v-if="txn.raw_message" class="modern-message-container pa-3">
                                            <div class="text-caption message-content">
                                                {{ txn.raw_message }}
                                            </div>
                                        </div>
                                    </div>

                                    <div class="d-flex align-center gap-2 mt-auto">
                                        <v-tooltip text="Mark as a transfer between your own accounts" location="top"
                                            open-delay="400">
                                            <template v-slot:activator="{ props }">
                                                <v-btn-toggle v-bind="props" :model-value="txn.is_transfer"
                                                    density="comfortable" variant="flat"
                                                    class="tactile-toggle-group transfer-toggle"
                                                    @update:model-value="txn.is_transfer = !!$event; if ($event) txn.exclude_from_reports = true">
                                                    <v-btn :value="true" size="x-small"
                                                        class="text-none px-3 rounded-pill"
                                                        :color="txn.is_transfer ? 'blue-darken-1' : ''">
                                                        <template v-slot:prepend>
                                                            <ArrowLeftRight :size="14" />
                                                        </template>
                                                        Transfer
                                                    </v-btn>
                                                </v-btn-toggle>
                                            </template>
                                        </v-tooltip>

                                        <v-tooltip text="Exclude this transaction from your budget and reports"
                                            location="top" open-delay="400">
                                            <template v-slot:activator="{ props }">
                                                <v-btn-toggle v-bind="props" :model-value="txn.exclude_from_reports"
                                                    density="comfortable" variant="flat"
                                                    class="tactile-toggle-group hide-toggle"
                                                    @update:model-value="txn.exclude_from_reports = !!$event">
                                                    <v-btn :value="true" size="x-small"
                                                        class="text-none px-3 rounded-pill"
                                                        :color="txn.exclude_from_reports ? 'grey-darken-2' : ''">
                                                        <template v-slot:prepend>
                                                            <EyeOff :size="14" />
                                                        </template>
                                                        Hide
                                                    </v-btn>
                                                </v-btn-toggle>
                                            </template>
                                        </v-tooltip>
                                    </div>

                                    <div class="modern-category-select pt-1">
                                        <div class="d-flex align-center gap-2">
                                            <span class="text-caption font-weight-black opacity-60 flex-shrink-0"
                                                style="width: 70px">Category</span>
                                            <v-autocomplete v-model="txn.category" :items="categoryOptions"
                                                item-title="title" item-value="value" placeholder="Select Category"
                                                variant="outlined" density="comfortable" rounded="lg" hide-details
                                                class="flex-grow-1" bg-color="surface">
                                                <template v-slot:prepend-inner>
                                                    <Tag :size="18" class="text-primary mr-2" />
                                                </template>
                                            </v-autocomplete>
                                        </div>
                                    </div>
                                    
                                    <div class="modern-account-select pt-1">
                                        <div class="d-flex align-center gap-2">
                                            <span class="text-caption font-weight-black opacity-60 flex-shrink-0"
                                                style="width: 70px">Account</span>
                                            <v-autocomplete v-model="txn.account_id" :items="accountOptions"
                                                item-title="title" item-value="value" placeholder="Select Account"
                                                variant="outlined" density="comfortable" rounded="lg" hide-details
                                                class="flex-grow-1" bg-color="surface">
                                                <template v-slot:prepend-inner>
                                                    <Landmark :size="18" class="text-primary mr-2" />
                                                </template>
                                            </v-autocomplete>
                                        </div>
                                    </div>

                                    <!-- Target Account (Conditional) -->
                                    <v-expand-transition>
                                        <div v-if="txn.is_transfer" class="modern-transfer-select pt-1">
                                            <div class="d-flex align-center gap-2">
                                                <span class="text-caption font-weight-black opacity-60 flex-shrink-0"
                                                    style="width: 70px">To</span>
                                                <v-autocomplete v-model="txn.to_account_id"
                                                    :items="accountOptions.filter(a => a.value !== txn.account_id)"
                                                    item-title="title" item-value="value" placeholder="Target Account"
                                                    variant="outlined" density="comfortable" rounded="lg" hide-details
                                                    class="flex-grow-1"></v-autocomplete>
                                            </div>
                                        </div>
                                    </v-expand-transition>
                                </v-card-text>

                                <!-- Tooling Footer -->
                                <div class="modern-card-footer px-3 py-2 d-flex align-center gap-1 border-t">
                                    <v-tooltip text="Discard this transaction" location="top" open-delay="400">
                                        <template v-slot:activator="{ props }">
                                            <v-btn v-bind="props" variant="tonal" size="small" color="error"
                                                @click="emit('rejectTriage', txn.id)"
                                                class="rounded-lg footer-action-btn">
                                                <Trash2 :size="16" />
                                            </v-btn>
                                        </template>
                                    </v-tooltip>

                                    <v-tooltip text="Map this merchant to an alias for better categorization"
                                        location="top" open-delay="400">
                                        <template v-slot:activator="{ props }">
                                            <v-btn v-bind="props" variant="tonal" size="small" color="primary"
                                                @click="openAliasModal(txn)" class="rounded-lg footer-action-btn">
                                                <MapPin :size="16" />
                                            </v-btn>
                                        </template>
                                    </v-tooltip>

                                    <v-tooltip text="View full transaction details and raw message" location="top"
                                        open-delay="400">
                                        <template v-slot:activator="{ props }">
                                            <v-btn v-bind="props" variant="tonal" size="small" color="secondary"
                                                @click="openTriageDetails(txn)" class="rounded-lg footer-action-btn">
                                                <Info :size="16" />
                                            </v-btn>
                                        </template>
                                    </v-tooltip>

                                    <v-spacer></v-spacer>

                                    <v-tooltip text="Approve and confirm this transaction" location="top"
                                        open-delay="400">
                                        <template v-slot:activator="{ props }">
                                            <v-btn v-bind="props" color="primary" variant="tonal" size="small"
                                                class="rounded-lg footer-action-btn"
                                                :disabled="!txn.category || txn.category === 'Uncategorized'"
                                                @click="emit('approveTriage', txn)">
                                                <Check :size="16" />
                                            </v-btn>
                                        </template>
                                    </v-tooltip>
                                </div>
                        </v-card>
                    </v-col>
                </v-row>

                <!-- Empty State -->
                <div v-if="triagePagination.total === 0" class="text-center py-16 animate-in">
                    <v-avatar size="100" color="success" variant="tonal" class="mb-6">
                        <CheckCircle2 :size="48" />
                    </v-avatar>
                    <h3 class="text-h4 font-weight-black">Inbox Zero!</h3>
                    <p class="text-subtitle-1 text-medium-emphasis mt-2">No new transactions waiting for review.</p>
                </div>

                <v-divider class="border-opacity-10"></v-divider>
                <div v-if="triagePagination.total > 0" class="d-flex align-center justify-end py-3 px-4 triage-footer">
                    <div class="d-flex align-center mr-8">
                        <span class="text-caption text-medium-emphasis mr-2">Rows per page:</span>
                        <v-menu>
                            <template v-slot:activator="{ props }">
                                <v-btn v-bind="props" variant="text" size="small" density="compact"
                                    class="text-caption font-weight-black px-1 no-hover-effect">
                                    {{ triagePagination.limit }}
                                    <ChevronDown :size="14" class="ml-1 opacity-60" />
                                </v-btn>
                            </template>
                            <v-list density="compact" class="rounded-lg border" elevation="2">
                                <v-list-item v-for="size in [12, 24, 60]" :key="size"
                                    @click="handleTriagePaginationLimitChange(size)" :active="triagePagination.limit === size" color="primary">
                                    <v-list-item-title class="text-caption font-weight-bold">{{ size }}</v-list-item-title>
                                </v-list-item>
                            </v-list>
                        </v-menu>
                    </div>
                    
                    <div class="text-caption font-weight-bold text-medium-emphasis mr-6">
                        {{ triagePagination.skip + 1 }}-{{ Math.min(triagePagination.skip + triagePagination.limit, triagePagination.total) }} of {{ triagePagination.total }}
                    </div>

                    <div class="d-flex align-center gap-1">
                        <v-btn icon variant="text" size="small" :disabled="triagePagination.skip === 0" 
                            @click="triageCurrentPage--">
                            <ChevronLeft :size="18" />
                        </v-btn>
                        <v-btn icon variant="text" size="small" 
                            :disabled="triagePagination.skip + triagePagination.limit >= triagePagination.total"
                            @click="triageCurrentPage++">
                            <ChevronRight :size="18" />
                        </v-btn>
                    </div>
                </div>
            </v-window-item>

            <!-- TRAINING TAB -->
            <v-window-item value="training">
                <v-alert type="info" variant="tonal" class="mb-6 rounded-xl" border="start" density="comfortable">
                    <template v-slot:prepend>
                        <Info :size="18" class="mr-2 text-info" />
                    </template>
                    <strong>Interactive Training</strong>: These messages look like transactions but could
                    not be parsed. Label them to help the system learn!
                </v-alert>

                <!-- Training Toolbar -->
                <v-card class="premium-glass-card mb-4 pa-3 no-hover" style="border-radius: 20px !important;">
                    <v-row align="center" no-gutters class="gap-3 px-2">
                        <!-- Left: Selection Group -->
                        <v-col cols="auto" class="d-flex align-center gap-2">
                            <v-checkbox-btn
                                :model-value="selectedTrainingIds.length === unparsedMessages.length && unparsedMessages.length > 0"
                                @update:model-value="toggleSelectAllTraining" color="primary" label="All"
                                hide-details density="comfortable" class="ml-1 font-weight-black"></v-checkbox-btn>

                            <v-fade-transition>
                                <v-tooltip v-if="selectedTrainingIds.length > 0"
                                    :text="`Dismiss ${selectedTrainingIds.length} selected messages`" location="top"
                                    open-delay="400">
                                    <template v-slot:activator="{ props }">
                                        <v-btn v-bind="props" color="error" variant="tonal" size="small" height="40"
                                            @click="emit('bulkDismissTraining')" rounded="lg" class="font-weight-black">
                                            <template v-slot:prepend>
                                                <Trash2 :size="16" />
                                            </template>
                                            Dismiss ({{ selectedTrainingIds.length }})
                                        </v-btn>
                                    </template>
                                </v-tooltip>
                            </v-fade-transition>
                        </v-col>

                        <v-divider vertical class="d-none d-md-block mx-1" />

                        <!-- Center: Search Group -->
                        <v-col cols="12" md="3" class="d-flex align-center">
                            <v-text-field :model-value="trainingSearchQuery"
                                @update:model-value="emit('update:trainingSearchQuery', $event)"
                                placeholder="Search sender, subject..." hide-details density="comfortable"
                                variant="outlined" rounded="lg" bg-color="surface" color="primary" clearable>
                                <template v-slot:prepend-inner>
                                    <Search :size="18" class="text-medium-emphasis mr-1" />
                                </template>
                            </v-text-field>
                        </v-col>

                        <v-spacer></v-spacer>

                        <!-- Right: Filter & Sort Group -->
                        <v-col cols="12" md="auto" class="d-flex align-center gap-2">
                            <v-fade-transition>
                                <v-btn v-if="trainingSenderFilter" variant="tonal" color="primary" size="small" height="40" 
                                    class="rounded-lg px-3 font-weight-black text-none" @click="emit('update:trainingSenderFilter', null)">
                                    <ScanSearch :size="16" class="mr-2" />
                                    Similar: {{ trainingSenderFilter }}
                                    <X :size="14" class="ml-2 opacity-50" />
                                </v-btn>
                            </v-fade-transition>

                            <v-tooltip text="Manage Spam Filters" location="top" open-delay="400">
                                <template v-slot:activator="{ props }">
                                    <v-btn v-bind="props" variant="tonal" color="error" size="small" height="40" width="40" class="rounded-lg" 
                                        @click="emit('update:showSpamManager', true); emit('fetchSpamFilters')">
                                        <ShieldOff :size="18" />
                                    </v-btn>
                                </template>
                            </v-tooltip>

                            <v-autocomplete :model-value="trainingSortKey"
                                @update:model-value="emit('update:trainingSortKey', $event)"
                                :items="[{ title: 'By Date', value: 'created_at' }, { title: 'By Sender', value: 'sender' }]"
                                item-title="title" item-value="value" hide-details density="comfortable"
                                variant="outlined" label="Sort" style="width: 140px" rounded="lg"
                                class="font-weight-bold" bg-color="surface" color="primary"></v-autocomplete>

                            <v-tooltip :text="`Sort by ${trainingSortOrder === 'asc' ? 'Descending' : 'Ascending'}`"
                                location="top" open-delay="400">
                                <template v-slot:activator="{ props }">
                                    <v-btn v-bind="props"
                                        @click="emit('update:trainingSortOrder', trainingSortOrder === 'asc' ? 'desc' : 'asc')"
                                        variant="tonal" size="small" height="40" width="40" color="primary"
                                        class="rounded-lg">
                                        <ArrowUp v-if="trainingSortOrder === 'asc'" :size="18" />
                                        <ArrowDown v-else :size="18" />
                                    </v-btn>
                                </template>
                            </v-tooltip>

                            <v-tooltip text="Refresh training data" location="top" open-delay="400">
                                <template v-slot:activator="{ props }">
                                    <v-btn v-bind="props" variant="text" size="small" height="40" width="40" class="rounded-lg"
                                        @click="emit('refreshTriage')">
                                        <RefreshCcw :size="18" />
                                    </v-btn>
                                </template>
                            </v-tooltip>
                        </v-col>
                    </v-row>
                </v-card>

                <!-- Training Grid -->
                <v-row>
                    <v-col v-for="msg in sortedTrainingMessages" :key="msg.id" cols="12" md="6" lg="6">
                        <v-card class="premium-glass-card training-card" variant="flat">
                            <!-- Dynamic Accent Glow (Primary for Training) -->
                            <div class="card-glow-accent triage-glow"></div>

                            <div class="card-modern-header px-4 pt-4 pb-2">
                                <div class="d-flex align-center gap-3 overflow-hidden">
                                    <v-checkbox-btn v-model="selectedTrainingIds" :value="msg.id" color="primary"
                                        density="comfortable" hide-details class="mt-n1"></v-checkbox-btn>

                                    <div class="flex-grow-1 min-width-0">
                                        <div
                                            class="text-subtitle-2 font-weight-black text-truncate modern-header-title mb-1">
                                            {{ msg.sender || 'Unknown Sender' }}
                                        </div>
                                        <div class="d-flex flex-wrap align-center gap-2 text-caption opacity-70">
                                            <span class="font-weight-bold">{{ formatDate(msg.created_at).day }}</span>
                                            <span class="opacity-30">•</span>
                                            <span class="text-uppercase tracking-wider font-weight-black opacity-50">{{
                                                msg.source }}</span>
                                            <v-chip v-if="msg.latitude" size="x-small" color="primary" variant="tonal" class="rounded-pill font-weight-bold" density="compact">
                                                <MapPin :size="10" class="mr-1" /> GPS
                                            </v-chip>
                                            <v-chip color="primary" size="x-small" variant="flat" class="ml-auto uppercase px-1 px-sm-2">Needs
                                                Training</v-chip>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <v-card-text class="flex-grow-1 px-4 py-2 d-flex flex-column gap-3">
                                <div v-if="msg.subject" class="text-caption font-weight-bold opacity-60">
                                    Subject: <span class="text-on-surface opacity-100">{{ msg.subject }}</span>
                                </div>

                                <div class="modern-message-container training-message-box pa-3">
                                    <div class="text-caption message-content training-content">
                                        {{ msg.raw_content }}
                                    </div>
                                </div>
                            </v-card-text>

                            <div class="modern-card-footer px-3 py-2 d-flex align-center gap-1 border-t mt-auto">
                                <v-tooltip text="Dismiss this message" location="top" open-delay="400">
                                    <template v-slot:activator="{ props }">
                                        <v-btn v-bind="props" variant="tonal" color="grey" size="small"
                                            class="rounded-lg footer-action-btn"
                                            @click="emit('dismissTraining', msg.id)">
                                            <Trash2 :size="16" />
                                        </v-btn>
                                    </template>
                                </v-tooltip>
                                <v-tooltip text="Mark as spam (block future)" location="top" open-delay="400">
                                    <template v-slot:activator="{ props }">
                                        <v-btn v-bind="props" variant="tonal" color="error" size="small"
                                            class="rounded-lg footer-action-btn"
                                            @click="emit('markAsSpam', msg.id)">
                                            <ShieldAlert :size="16" />
                                        </v-btn>
                                    </template>
                                </v-tooltip>
                                <v-tooltip text="Find similar messages from this sender" location="top" open-delay="400">
                                    <template v-slot:activator="{ props }">
                                        <v-btn v-bind="props" variant="tonal" color="primary" size="small"
                                            class="rounded-lg footer-action-btn"
                                            @click="msg.sender ? emit('findSimilar', msg.sender) : null">
                                            <ScanSearch :size="16" />
                                        </v-btn>
                                    </template>
                                </v-tooltip>
                                <v-spacer></v-spacer>
                                <v-tooltip text="Label this message as a transaction to train the system" location="top"
                                    open-delay="400">
                                    <template v-slot:activator="{ props }">
                                        <v-btn v-bind="props" color="primary" variant="tonal" size="small"
                                            class="rounded-lg footer-action-btn" @click="emit('startLabeling', msg)">
                                            <Sparkles :size="16" />
                                        </v-btn>
                                    </template>
                                </v-tooltip>
                            </div>
                        </v-card>
                    </v-col>
                </v-row>

                <!-- Empty State -->
                <div v-if="trainingPagination.total === 0" class="text-center py-16 animate-in">
                    <v-avatar size="100" color="success" variant="tonal" class="mb-6">
                        <ShieldCheck :size="48" />
                    </v-avatar>
                    <h3 class="text-h4 font-weight-black">All Clear!</h3>
                    <p class="text-subtitle-1 text-medium-emphasis mt-2">No unparsed messages waiting for training.</p>
                </div>

                <v-divider class="border-opacity-10"></v-divider>
                <div v-if="trainingPagination.total > 0" class="d-flex align-center justify-end py-3 px-4 triage-footer">
                    <div class="d-flex align-center mr-8">
                        <span class="text-caption text-medium-emphasis mr-2">Rows per page:</span>
                        <v-menu>
                            <template v-slot:activator="{ props }">
                                <v-btn v-bind="props" variant="text" size="small" density="compact"
                                    class="text-caption font-weight-black px-1 no-hover-effect">
                                    {{ trainingPagination.limit }}
                                    <ChevronDown :size="14" class="ml-1 opacity-60" />
                                </v-btn>
                            </template>
                            <v-list density="compact" class="rounded-lg border" elevation="2">
                                <v-list-item v-for="size in [12, 24, 60]" :key="size"
                                    @click="handleTrainingPaginationLimitChange(size)" :active="trainingPagination.limit === size" color="primary">
                                    <v-list-item-title class="text-caption font-weight-bold">{{ size }}</v-list-item-title>
                                </v-list-item>
                            </v-list>
                        </v-menu>
                    </div>
                    
                    <div class="text-caption font-weight-bold text-medium-emphasis mr-6">
                        {{ trainingPagination.skip + 1 }}-{{ Math.min(trainingPagination.skip + trainingPagination.limit, trainingPagination.total) }} of {{ trainingPagination.total }}
                    </div>

                    <div class="d-flex align-center gap-1">
                        <v-btn icon variant="text" size="small" :disabled="trainingPagination.skip === 0" 
                            @click="trainingCurrentPage--">
                            <ChevronLeft :size="18" />
                        </v-btn>
                        <v-btn icon variant="text" size="small" 
                            :disabled="trainingPagination.skip + trainingPagination.limit >= trainingPagination.total"
                            @click="trainingCurrentPage++">
                            <ChevronRight :size="18" />
                        </v-btn>
                    </div>
                </div>
            </v-window-item>
        </v-window>

        <!-- Details Modal -->
        <v-dialog v-model="triageDetailsDialog" max-width="600" persistent transition="dialog-bottom-transition">
            <v-card v-if="selectedTriageTxn" class="rounded-xl overflow-hidden">
                <v-toolbar color="primary" density="comfortable">
                    <v-toolbar-title class="text-subtitle-1 font-weight-bold">Transaction Details</v-toolbar-title>
                    <v-spacer></v-spacer>
                    <v-tooltip text="Close details" location="bottom" open-delay="400">
                        <template v-slot:activator="{ props }">
                            <v-btn v-bind="props" variant="text" @click="triageDetailsDialog = false">
                                <X :size="20" />
                            </v-btn>
                        </template>
                    </v-tooltip>
                </v-toolbar>

                <v-card-text class="pt-6">
                    <div class="d-flex align-center justify-space-between mb-6">
                        <div>
                            <div class="text-h6 font-weight-black">{{ selectedTriageTxn.recipient ||
                                selectedTriageTxn.description }}</div>
                            <div class="text-caption text-medium-emphasis">
                                {{ formatDate(selectedTriageTxn.date).day }} • {{
                                    formatDate(selectedTriageTxn.date).meta }}
                            </div>
                        </div>
                        <div class="text-right">
                            <div class="text-h5 font-weight-black"
                                :class="Number(selectedTriageTxn?.amount || 0) < 0 ? 'text-error' : 'text-success'">
                                {{ formatAmount(Math.abs(Number(selectedTriageTxn?.amount || 0))) }}
                            </div>
                            <div class="text-caption text-medium-emphasis">{{ Number(selectedTriageTxn?.amount || 0) < 0 ? 'DEBIT'
                                : 'CREDIT' }}</div>
                            </div>
                        </div>

                        <v-divider class="mb-6"></v-divider>

                        <v-row>
                            <v-col cols="12">
                                <v-label class="text-caption font-weight-bold mb-2">Account</v-label>
                                <v-autocomplete v-model="selectedTriageTxn.account_id" :items="accountOptions"
                                    item-title="title" item-value="value" density="comfortable" variant="outlined"
                                    hide-details>
                                    <template v-slot:prepend-inner>
                                        <Landmark :size="18" class="opacity-60" />
                                    </template>
                                </v-autocomplete>
                            </v-col>

                            <v-col cols="12">
                                <v-autocomplete v-model="selectedTriageTxn.category" :items="categoryOptions"
                                    item-title="title" item-value="value" placeholder="Select Category"
                                    variant="outlined" density="comfortable" rounded="lg" hide-details>
                                    <template v-slot:prepend-inner>
                                        <Tag :size="18" class="opacity-60" />
                                    </template>
                                </v-autocomplete>
                            </v-col>

                            <v-col v-if="selectedTriageTxn?.is_transfer" cols="12">
                                <v-label class="text-caption font-weight-bold mb-2">
                                    {{ Number(selectedTriageTxn?.amount || 0) < 0 ? 'Transfer To' : 'Transfer From' }} </v-label>
                                        <v-autocomplete v-model="selectedTriageTxn.to_account_id"
                                            :items="accountOptions.filter(a => a.value !== (selectedTriageTxn?.account_id || ''))"
                                            item-title="title" item-value="value" density="comfortable"
                                            variant="outlined" hide-details></v-autocomplete>
                            </v-col>
                        </v-row>

                        <v-divider class="my-6"></v-divider>

                        <div class="d-flex flex-column gap-3">
                            <v-switch v-model="selectedTriageTxn.is_transfer" color="info" label="Internal Transfer"
                                density="comfortable" hide-details inset
                                @update:model-value="selectedTriageTxn.exclude_from_reports = selectedTriageTxn.is_transfer"></v-switch>

                            <v-switch v-model="selectedTriageTxn.exclude_from_reports" color="warning"
                                label="Hide in Reports" density="comfortable" hide-details inset></v-switch>
                        </div>

                        <div v-if="selectedTriageTxn.raw_message" class="mt-6">
                            <v-label class="text-caption font-weight-bold mb-2">Raw Message</v-label>
                            <div class="bg-grey-lighten-4 pa-4 rounded-lg text-caption italic border">
                                {{ selectedTriageTxn.raw_message }}
                            </div>
                        </div>
                </v-card-text>

                <v-divider></v-divider>

                <v-card-actions class="pa-4">
                    <v-spacer></v-spacer>
                    <v-tooltip text="Discard changes and close" location="top" open-delay="400">
                        <template v-slot:activator="{ props }">
                            <v-btn v-bind="props" variant="text" color="grey-darken-1"
                                @click="triageDetailsDialog = false" class="text-none">
                                Close
                            </v-btn>
                        </template>
                    </v-tooltip>
                    <v-tooltip text="Save changes and return to triage" location="top" open-delay="400">
                        <template v-slot:activator="{ props }">
                            <v-btn v-bind="props" color="primary" variant="elevated" class="text-none px-6 rounded-lg"
                                @click="saveTriageDetails">
                                Apply Changes
                            </v-btn>
                        </template>
                    </v-tooltip>
                </v-card-actions>
            </v-card>
        </v-dialog>

        <!-- Add Alias Modal -->
        <MerchantAliasModal v-model="showAliasModal" :initial-pattern="aliasForm.pattern"
            :initial-alias="aliasForm.alias" @saved="emit('refreshTriage')" />

        <!-- Discard Confirmation Dialog (Triage) -->
        <v-dialog :model-value="showDiscardConfirm" @update:model-value="emit('update:showDiscardConfirm', $event)"
            max-width="400">
            <v-card class="rounded-xl border border-error">
                <v-card-text class="pa-6 text-center">
                    <v-avatar color="error" variant="tonal" size="56" class="mb-4">
                        <Trash2 :size="28" />
                    </v-avatar>
                    <div class="text-h6 font-weight-black mb-2">
                        {{ triageIdToDiscard ? 'Discard Transaction?' : `Discard ${selectedTriageIds.length} Transactions?` }}
                    </div>
                    <p class="text-body-2 text-medium-emphasis mb-6">
                        This action will permanently remove the selected transaction(s) from your inbox.
                    </p>

                    <v-checkbox :model-value="createIgnoreRule"
                        @update:model-value="emit('update:createIgnoreRule', !!$event)"
                        label="Ignore this pattern in future" color="error" density="compact" hide-details
                        class="mb-6 font-weight-bold d-flex justify-center"></v-checkbox>

                    <div class="d-flex gap-3 justify-center">
                        <v-tooltip text="Keep these transactions" location="bottom" open-delay="400">
                            <template v-slot:activator="{ props }">
                                <v-btn v-bind="props" variant="tonal" @click="emit('update:showDiscardConfirm', false)"
                                    rounded="lg" class="px-6 font-weight-bold text-none">Cancel</v-btn>
                            </template>
                        </v-tooltip>
                        <v-tooltip text="Permanently remove selected items" location="bottom" open-delay="400">
                            <template v-slot:activator="{ props }">
                                <v-btn v-bind="props" color="error" variant="elevated" rounded="lg" class="px-6 font-weight-bold text-none"
                                    @click="triageIdToDiscard ? emit('confirmDiscard') : emit('confirmBulkDiscard')">
                                    Discard
                                </v-btn>
                            </template>
                        </v-tooltip>
                    </div>
                </v-card-text>
            </v-card>
        </v-dialog>

        <!-- Discard Confirmation Dialog (Training) -->
        <v-dialog :model-value="showTrainingDiscardConfirm"
            @update:model-value="emit('update:showTrainingDiscardConfirm', $event)" max-width="400">
            <v-card class="rounded-xl border border-error">
                <v-card-text class="pa-6 text-center">
                    <v-avatar color="error" variant="tonal" size="56" class="mb-4">
                        <Trash2 :size="28" />
                    </v-avatar>
                    <div class="text-h6 font-weight-black mb-2">
                        {{ trainingIdToDiscard ? 'Dismiss Message?' : `Dismiss ${selectedTrainingIds.length} Messages?` }}
                    </div>
                    <p class="text-body-2 text-medium-emphasis mb-6">
                        This action will permanently remove these unparsed messages from training.
                    </p>
                    
                    <v-checkbox :model-value="createIgnoreRule"
                        @update:model-value="emit('update:createIgnoreRule', !!$event)"
                        label="Don't show this sender again" color="error" density="compact" hide-details
                        class="mb-6 font-weight-bold d-flex justify-center"></v-checkbox>

                    <div class="d-flex gap-3 justify-center">
                        <v-tooltip text="Keep these messages" location="bottom" open-delay="400">
                            <template v-slot:activator="{ props }">
                                <v-btn v-bind="props" variant="tonal" @click="emit('update:showTrainingDiscardConfirm', false)"
                                    rounded="lg" class="px-6 font-weight-bold text-none">Cancel</v-btn>
                            </template>
                        </v-tooltip>
                        <v-tooltip text="Dismiss these messages and clear them from training" location="bottom"
                            open-delay="400">
                            <template v-slot:activator="{ props }">
                                <v-btn v-bind="props" color="error" variant="elevated" rounded="lg" class="px-6 font-weight-bold text-none"
                                    @click="trainingIdToDiscard ? emit('confirmTrainingDiscard') : emit('confirmBulkTrainingDiscard')">
                                    Dismiss
                                </v-btn>
                            </template>
                        </v-tooltip>
                    </div>
                </v-card-text>
            </v-card>
        </v-dialog>

        <!-- Training Modal -->
        <TransactionTrainingModal :model-value="showLabelForm"
            @update:model-value="emit('update:showLabelForm', $event)" :selected-message="selectedMessage"
            :label-form="labelForm" :categories="categories" @submit="emit('handleLabelSubmit')" />

        <!-- Spam Manager Modal -->
        <v-dialog :model-value="showSpamManager" @update:model-value="emit('update:showSpamManager', $event)" max-width="600" transition="dialog-bottom-transition">
            <v-card class="rounded-xl overflow-hidden">
                <v-toolbar color="error" density="comfortable">
                    <ShieldOff :size="20" class="ml-4 mr-2" />
                    <v-toolbar-title class="text-subtitle-1 font-weight-bold">Spam Filter Management</v-toolbar-title>
                    <v-spacer></v-spacer>
                    <v-btn variant="text" @click="emit('update:showSpamManager', false)">
                        <X :size="20" />
                    </v-btn>
                </v-toolbar>

                <v-card-text class="pa-0" style="min-height: 400px; max-height: 70vh; overflow-y: auto;">
                    <v-alert v-if="spamFilters.length === 0" type="info" variant="tonal" class="ma-4 rounded-lg">
                        You haven't blocked any senders yet.
                    </v-alert>

                    <v-list v-else lines="two" class="bg-transparent">
                        <v-list-item v-for="filter in spamFilters" :key="filter.id" class="border-b px-6">
                            <template v-slot:prepend>
                                <v-avatar color="error" variant="tonal" size="40">
                                    <ShieldAlert :size="20" />
                                </v-avatar>
                            </template>
                            
                            <v-list-item-title class="font-weight-black">
                                {{ filter.sender || 'Unknown Sender' }}
                            </v-list-item-title>
                            <v-list-item-subtitle class="text-caption opacity-70">
                                <span v-if="filter.subject" class="d-block">Subject: {{ filter.subject }}</span>
                                <span class="text-uppercase tracking-wider font-weight-bold d-inline-flex align-center gap-1">
                                    <span class="opacity-50">Source:</span> {{ filter.source }}
                                    <span class="mx-2 opacity-20">|</span>
                                    <span class="opacity-50">Blocked:</span> <span class="text-error">{{ filter.count_blocked || 0 }} times</span>
                                </span>
                            </v-list-item-subtitle>

                            <template v-slot:append>
                                <v-btn variant="tonal" color="grey" size="small" rounded="lg" 
                                    @click="emit('removeSpamFilter', filter.id)">
                                    Unblock
                                </v-btn>
                            </template>
                        </v-list-item>
                    </v-list>
                </v-card-text>
            </v-card>
        </v-dialog>
    </div>
</template>

<script setup lang="ts">
import { computed, ref, reactive } from 'vue'
import MerchantAliasModal from '@/components/MerchantAliasModal.vue'
import TransactionTrainingModal from './TransactionTrainingModal.vue'
import { useCurrency } from '@/composables/useCurrency'
import {
    Search,
    ArrowUpNarrowWide,
    ArrowDownNarrowWide,
    ArrowLeftRight,
    ArrowUp,
    ArrowDown,
    Trash2,
    RotateCw,
    Landmark,
    ShieldAlert,
    MapPin,
    Info,
    Check,
    Sparkles,
    X,
    Zap,
    CheckCircle2,
    ShieldCheck,
    RefreshCcw,
    ChevronLeft,
    ChevronRight,
    ChevronDown,
    ShieldOff,
    ScanSearch
} from 'lucide-vue-next'
export interface AccountItem {
    id: string
    name: string
    [key: string]: any
}

export interface CategoryItem {
    id: string
    name: string
    icon?: string
    color?: string
    subcategories?: CategoryItem[]
    [key: string]: any
}

export interface TriageTransaction {
    id: string
    date: string
    amount: number | string
    recipient?: string
    description?: string
    source?: string
    external_id?: string
    account_id: string
    raw_message?: string
    is_transfer?: boolean
    exclude_from_reports?: boolean
    category?: string
    to_account_id?: string
    [key: string]: any
}

export interface UnparsedMessage {
    id: string
    created_at: string
    sender?: string
    source?: string
    subject?: string
    raw_content?: string
    [key: string]: any
}

// Props
const props = defineProps<{
    activeSubTab: 'pending' | 'training'
    accounts: AccountItem[]
    categories: CategoryItem[]
    triageTransactions: TriageTransaction[]
    triagePagination: { total: number; limit: number; skip: number }
    triageSearchQuery: string
    triageSourceFilter: string
    triageSortKey: string
    triageSortOrder: 'asc' | 'desc'
    unparsedMessages: UnparsedMessage[]
    trainingPagination: { total: number; limit: number; skip: number }
    trainingSearchQuery: string
    trainingSortKey: string
    trainingSortOrder: 'asc' | 'desc'
    trainingSenderFilter: string | null
    trainingSubjectFilter: string | null
    spamFilters: any[]
    showSpamManager: boolean
    // Confirmation States
    showDiscardConfirm: boolean
    showTrainingDiscardConfirm: boolean
    createIgnoreRule: boolean
    triageIdToDiscard: string | null
    trainingIdToDiscard: string | null
    // Training Modal Props
    showLabelForm: boolean
    selectedMessage: any
    labelForm: any
}>()

// Emits
const emit = defineEmits<{
    'update:activeSubTab': [value: 'pending' | 'training']
    'update:triageSearchQuery': [value: string]
    'update:triageSourceFilter': [value: string]
    'update:triageSortKey': [value: string]
    'update:triageSortOrder': [value: 'asc' | 'desc']
    'update:triagePagination': [value: { total: number; limit: number; skip: number }]
    'update:trainingSortKey': [value: string]
    'update:trainingSortOrder': [value: 'asc' | 'desc']
    'update:trainingPagination': [value: { total: number; limit: number; skip: number }]
    'update:trainingSearchQuery': [value: string]
    'update:trainingSenderFilter': [value: string | null]
    'update:trainingSubjectFilter': [value: string | null]
    'update:showSpamManager': [value: boolean]
    'approveTriage': [txn: TriageTransaction]
    'rejectTriage': [id: string]
    'bulkRejectTriage': []
    'startLabeling': [msg: UnparsedMessage]
    'dismissTraining': [id: string]
    'bulkDismissTraining': []
    'markAsSpam': [id: string]
    'findSimilar': [sender: string]
    'removeSpamFilter': [id: string]
    'fetchSpamFilters': []
    'refreshTriage': []
    'update:showDiscardConfirm': [value: boolean]
    'update:showTrainingDiscardConfirm': [value: boolean]
    'update:createIgnoreRule': [value: boolean]
    'confirmDiscard': []
    'confirmTrainingDiscard': []
    'confirmBulkDiscard': []
    'confirmBulkTrainingDiscard': []
    'update:showLabelForm': [value: boolean]
    'handleLabelSubmit': []
}>()

// Local State
const selectedTriageIds = defineModel<string[]>('selectedTriageIds', { default: [] })
const selectedTrainingIds = defineModel<string[]>('selectedTrainingIds', { default: [] })
// Computed Interface for Tabs
const activeTab = computed({
    get: () => props.activeSubTab,
    set: (val) => emit('update:activeSubTab', val)
})

const accountOptions = computed(() => {
    return props.accounts.map(a => ({ title: a.name, value: a.id }))
})

const categoryOptions = computed(() => {
    const list: { title: string; value: string }[] = []
    const flatten = (cats: CategoryItem[], depth = 0) => {
        cats.forEach(c => {
            const prefix = depth > 0 ? '　'.repeat(depth) + '└ ' : ''
            list.push({
                title: `${prefix}${c.icon || '🏷️'} ${c.name}`,
                value: c.name
            })
            if (c.subcategories && c.subcategories.length > 0) {
                flatten(c.subcategories, depth + 1)
            }
        })
    }
    flatten(props.categories)
    if (!list.find(o => o.value === 'Uncategorized')) {
        list.push({ title: '🏷️ Uncategorized', value: 'Uncategorized' })
    }
    return list
})

const filteredTriageTransactions = computed(() => {
    let filtered = props.triageTransactions

    if (props.triageSearchQuery) {
        const q = props.triageSearchQuery.toLowerCase()
        filtered = filtered.filter(t =>
            (t.recipient && t.recipient.toLowerCase().includes(q)) ||
            (t.description && t.description.toLowerCase().includes(q)) ||
            (t.external_id && t.external_id.toLowerCase().includes(q)) ||
            (t.amount && String(t.amount).includes(q))
        )
    }

    if (props.triageSourceFilter && props.triageSourceFilter !== 'ALL') {
        filtered = filtered.filter(t => t.source === props.triageSourceFilter)
    }

    return filtered
})

const triageCurrentPage = computed({
    get: () => Math.floor(props.triagePagination.skip / props.triagePagination.limit) + 1,
    set: (val) => emit('update:triagePagination', { ...props.triagePagination, skip: (val - 1) * props.triagePagination.limit })
})

const trainingCurrentPage = computed({
    get: () => Math.floor(props.trainingPagination.skip / props.trainingPagination.limit) + 1,
    set: (val) => emit('update:trainingPagination', { ...props.trainingPagination, skip: (val - 1) * props.trainingPagination.limit })
})

const sortedTrainingMessages = computed(() => {
    let messages = [...props.unparsedMessages]
    const key = props.trainingSortKey as any
    messages.sort((a, b) => {
        const valA = a[key]
        const valB = b[key]
        if (valA < valB) return props.trainingSortOrder === 'asc' ? -1 : 1
        if (valA > valB) return props.trainingSortOrder === 'asc' ? 1 : -1
        return 0
    })
    return messages
})

// Methods
function getAccountName(id: string) {
    const acc = props.accounts.find(a => a.id === id)
    return acc ? acc.name : 'Unknown Account'
}

function formatDate(dateStr: string) {
    if (!dateStr) return { day: 'N/A', meta: '' }

    const d = new Date(dateStr)
    if (isNaN(d.getTime())) {
        return { day: '?', meta: dateStr.split('T')[0] || dateStr }
    }

    const today = new Date()
    const yesterday = new Date(today)
    yesterday.setDate(yesterday.getDate() - 1)

    const time = d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })

    if (d.toDateString() === today.toDateString()) {
        return { day: 'Today', meta: time }
    }
    if (d.toDateString() === yesterday.toDateString()) {
        return { day: 'Yesterday', meta: time }
    }

    const currentYear = today.getFullYear()
    const txnYear = d.getFullYear()

    let formatOptions: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric' }
    if (txnYear !== currentYear) {
        formatOptions.year = 'numeric'
    }

    const monthDay = d.toLocaleDateString('en-US', formatOptions)
    return {
        day: monthDay,
        meta: time
    }
}

function toggleSelectAllTriage() {
    if (selectedTriageIds.value.length === filteredTriageTransactions.value.length && filteredTriageTransactions.value.length > 0) {
        selectedTriageIds.value = []
    } else {
        selectedTriageIds.value = filteredTriageTransactions.value.map(t => t.id)
    }
}

function toggleSelectAllTraining() {
    if (selectedTrainingIds.value.length === props.unparsedMessages.length && props.unparsedMessages.length > 0) {
        selectedTrainingIds.value = []
    } else {
        selectedTrainingIds.value = props.unparsedMessages.map(m => m.id)
    }
}



function handleTriagePaginationLimitChange(newLimit: number) {
    emit('update:triagePagination', { ...props.triagePagination, limit: newLimit, skip: 0 })
}

function handleTrainingPaginationLimitChange(newLimit: number) {
    emit('update:trainingPagination', { ...props.trainingPagination, limit: newLimit, skip: 0 })
}

const showAliasModal = ref(false)
const aliasForm = reactive({
    pattern: '',
    alias: '',
    update_past: false
})

function openAliasModal(txn: TriageTransaction) {
    aliasForm.pattern = txn.description || txn.recipient || ''
    aliasForm.alias = txn.recipient || ''
    showAliasModal.value = true
}

// --- Triage Details Modal ---
const triageDetailsDialog = ref(false)
const selectedTriageTxn = ref<TriageTransaction | null>(null)

function openTriageDetails(txn: TriageTransaction) {
    selectedTriageTxn.value = JSON.parse(JSON.stringify(txn)) // Deep copy
    triageDetailsDialog.value = true
}

function saveTriageDetails() {
    if (!selectedTriageTxn.value) return
    const index = props.triageTransactions.findIndex(t => t.id === selectedTriageTxn.value?.id)
    if (index !== -1) {
        Object.assign(props.triageTransactions[index], selectedTriageTxn.value)
    }
    triageDetailsDialog.value = false
}

const { formatAmount } = useCurrency()
</script>

<style scoped>
.premium-glass-card {
    background: rgba(var(--v-theme-surface), 0.7) !important;
    backdrop-filter: blur(10px) !important;
    border: 1px solid rgba(var(--v-border-color), 0.1) !important;
    border-radius: 20px !important;
    box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07) !important;
    transition: all 0.4s cubic-bezier(0.23, 1, 0.32, 1);
    position: relative;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}

.premium-glass-card:hover {
    border-color: rgba(var(--v-theme-primary), 0.3) !important;
    transform: translateY(-4px);
}

.premium-glass-card.is-selected {
    border: 2px solid rgb(var(--v-theme-primary)) !important;
    background: rgba(var(--v-theme-primary), 0.05) !important;
}

.card-glow-accent {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: transparent;
    transition: all 0.3s ease;
    z-index: 2;
}

.is-debit .card-glow-accent {
    background: linear-gradient(90deg, rgba(var(--v-theme-error), 0.8), transparent);
    box-shadow: 0 0 15px rgba(var(--v-theme-error), 0.4);
}

.is-credit .card-glow-accent {
    background: linear-gradient(90deg, rgba(var(--v-theme-success), 0.8), transparent);
    box-shadow: 0 0 15px rgba(var(--v-theme-success), 0.4);
}

.training-glow {
    background: linear-gradient(90deg, rgba(var(--v-theme-warning), 0.8), transparent) !important;
    box-shadow: 0 0 15px rgba(var(--v-theme-warning), 0.4) !important;
}

.modern-header-title {
    color: rgba(var(--v-theme-on-surface), 0.9);
    letter-spacing: -0.3px;
    line-height: 1.2;
}

.amount-hero-section {
    background: rgba(var(--v-theme-on-surface), 0.02);
    border-top: 1px solid rgba(var(--v-border-color), 0.05);
    border-bottom: 1px solid rgba(var(--v-border-color), 0.05);
}

.amount-hero-text {
    font-size: 2.2rem !important;
    font-weight: 900 !important;
    line-height: 1;
    font-family: 'Inter', sans-serif;
    letter-spacing: -1.5px;
}

.modern-message-container {
    background: rgba(var(--v-theme-on-surface), 0.03);
    border-radius: 16px;
    border: 1px dashed rgba(var(--v-border-color), 0.2);
    position: relative;
    overflow: hidden;
}

.training-message-box {
    background: rgba(var(--v-theme-warning), 0.03) !important;
    border: 1px solid rgba(var(--v-theme-warning), 0.1) !important;
}

.message-content {
    line-height: 1.5;
    color: rgba(var(--v-theme-on-surface), 0.7);
    font-style: italic;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.training-content {
    font-family: 'Fira Code', monospace !important;
    font-style: normal !important;
    -webkit-line-clamp: 5 !important;
}

.tactile-toggle-group {
    background: rgba(var(--v-theme-on-surface), 0.04);
    padding: 3px;
    border-radius: 50px;
    border: 1px solid rgba(var(--v-border-color), 0.05) !important;
}

.tactile-toggle-group :deep(.v-btn) {
    height: 28px !important;
    font-size: 11px !important;
    font-weight: 800 !important;
    letter-spacing: 0.5px;
    border: none !important;
}

.modern-card-footer {
    background: rgba(var(--v-theme-on-surface), 0.02);
    backdrop-filter: blur(5px);
}

.footer-action-btn {
    transition: all 0.2s ease;
}

.footer-action-btn:hover {
    color: rgb(var(--v-theme-primary)) !important;
}

.no-hover-effect:hover {
    background: rgba(var(--v-theme-on-surface), 0.05) !important;
}

.triage-footer {
    background: rgba(var(--v-theme-on-surface), 0.01);
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

.gap-2 {
    gap: 8px;
}

.gap-3 {
    gap: 12px;
}

.gap-4 {
    gap: 16px;
}

.border-thin {
    border: 1px solid rgba(var(--v-border-color), 0.15) !important;
}

.tracking-wider {
    letter-spacing: 1px;
}

.tracking-widest {
    letter-spacing: 2px;
}

.no-hover:hover {
    transform: none !important;
}
</style>
