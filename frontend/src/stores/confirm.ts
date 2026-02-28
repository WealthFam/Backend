import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useConfirmStore = defineStore('confirm', () => {
    const isOpen = ref(false)
    const title = ref('')
    const message = ref('')
    const confirmText = ref('Confirm')
    const cancelText = ref('Cancel')

    let resolvePromise: ((value: boolean) => void) | null = null

    function prompt(
        msg: string,
        customTitle: string = 'Confirmation',
        customConfirmText: string = 'Yes',
        customCancelText: string = 'No'
    ): Promise<boolean> {
        title.value = customTitle
        message.value = msg
        confirmText.value = customConfirmText
        cancelText.value = customCancelText
        isOpen.value = true

        return new Promise<boolean>((resolve) => {
            resolvePromise = resolve
        })
    }

    function agree() {
        isOpen.value = false
        if (resolvePromise) {
            resolvePromise(true)
            resolvePromise = null
        }
    }

    function cancel() {
        isOpen.value = false
        if (resolvePromise) {
            resolvePromise(false)
            resolvePromise = null
        }
    }

    return {
        isOpen,
        title,
        message,
        confirmText,
        cancelText,
        prompt,
        agree,
        cancel
    }
})
