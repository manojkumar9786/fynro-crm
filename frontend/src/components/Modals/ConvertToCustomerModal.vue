<template>
  <Dialog v-model:open="show" :size="'xl'">
    <template #body-header>
      <div class="mb-6 flex items-center justify-between">
        <div>
          <h3 class="text-3xl-semibold leading-6 text-ink-gray-9">
            {{ __('Convert to Customer') }}
          </h3>
          <p class="mt-1 text-base text-ink-gray-5">
            {{ __('Lead data will be copied into a new Customer record') }}
          </p>
        </div>
        <Button icon="lucide-x" variant="ghost" @click="show = false" />
      </div>
    </template>
    <template #default>
      <div class="space-y-4">
        <div class="rounded-lg border bg-surface-gray-1 p-4">
          <div class="flex items-center gap-3">
            <div class="flex h-10 w-10 items-center justify-center rounded-full bg-green-100">
              <span class="text-lg">🏢</span>
            </div>
            <div>
              <div class="text-base-semibold text-ink-gray-9">{{ lead.lead_name || lead.first_name }}</div>
              <div class="text-sm text-ink-gray-5">{{ lead.email }}</div>
            </div>
          </div>
        </div>
        <div class="text-sm text-ink-gray-5">
          {{ __('All lead details will be copied, including custom fields, and the lead owner will become the owner of the new record.') }}
          <div v-if="ownerName" class="mt-1 text-ink-gray-7">
            {{ __('Owner') }}: {{ ownerName }}
          </div>
        </div>
      </div>
      <ErrorMessage class="mt-4" :message="error" />
    </template>
    <template #actions>
      <div class="flex justify-end gap-2">
        <Button :label="__('Cancel')" variant="ghost" @click="show = false" />
        <Button
          :label="__('Convert to Customer')"
          variant="solid"
          theme="green"
          :loading="loading"
          @click="convertToCustomer"
        />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { Dialog, call, toast } from 'frappe-ui'
import { usersStore } from '@/stores/users'
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  lead: { type: Object, required: true },
})

const show = defineModel({ type: Boolean })
const { getUser } = usersStore()
const ownerName = computed(
  () => props.lead.lead_owner && getUser(props.lead.lead_owner)?.full_name,
)
const router = useRouter()
const error = ref('')
const loading = ref(false)

async function convertToCustomer() {
  error.value = ''
  loading.value = true
  try {
    const customer = await call(
      'crm.fcrm.doctype.crm_lead.crm_lead.convert_to_customer',
      { lead: props.lead.name },
    )
    if (customer) {
      show.value = false
      toast.success(__('Lead converted to Customer successfully'))
      router.push({ name: 'Customer', params: { customerId: customer } })
    }
  } catch (err) {
    error.value = err.messages?.[0] || __('Error converting to Customer')
  } finally {
    loading.value = false
  }
}
</script>
