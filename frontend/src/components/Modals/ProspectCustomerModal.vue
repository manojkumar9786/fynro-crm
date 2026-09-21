<template>
  <Dialog v-model:open="show" :size="'3xl'">
    <template #body>
      <div class="bg-surface-elevation-2 px-4 pb-6 pt-5 sm:px-6">
        <div class="mb-5 flex items-center justify-between">
          <div>
            <h3 class="text-3xl-semibold leading-6 text-ink-gray-9">
              {{ config.title }}
            </h3>
          </div>
          <div class="flex items-center gap-1">
            <Button
              v-if="isManager() && !isMobileView"
              variant="ghost"
              class="w-7"
              :tooltip="__('Edit Fields Layout')"
              :icon="EditIcon"
              @click="openQuickEntryModal"
            />
            <Button
              variant="ghost"
              class="w-7"
              icon="lucide-x"
              @click="show = false"
            />
          </div>
        </div>
        <div>
          <FieldLayout v-if="tabs.data" :tabs="tabs.data" :data="record.doc" />
          <ErrorMessage v-if="error" class="mt-4" :message="__(error)" />
        </div>
      </div>
      <div class="px-4 pb-7 pt-4 sm:px-6">
        <div class="flex flex-row-reverse gap-2">
          <Button
            variant="solid"
            :label="__('Create')"
            :loading="isCreating"
            @click="createRecord"
          />
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import EditIcon from '@/components/Icons/EditIcon.vue'
import FieldLayout from '@/components/FieldLayout/FieldLayout.vue'
import { usersStore } from '@/stores/users'
import { isMobileView } from '@/composables/settings'
import { showQuickEntryModal, quickEntryProps } from '@/composables/modals'
import { parseColor } from '@/utils'
import { createResource, createListResource } from 'frappe-ui'
import { useDocument } from '@/data/document'
import { computed, onMounted, ref, nextTick } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  doctype: {
    type: String,
    required: true,
    validator: (value) => ['CRM Prospect', 'CRM Customer'].includes(value),
  },
  defaults: { type: Object, default: () => ({}) },
})

const CONFIGS = {
  'CRM Prospect': {
    title: __('Create Prospect'),
    ownerField: 'prospect_owner',
    statusDoctype: 'CRM Prospect Status',
    routeName: 'Prospect',
    routeParam: 'prospectId',
  },
  'CRM Customer': {
    title: __('Create Customer'),
    ownerField: 'customer_owner',
    statusDoctype: 'CRM Customer Status',
    routeName: 'Customer',
    routeParam: 'customerId',
  },
}

const config = computed(() => CONFIGS[props.doctype])

const { getUser, isManager } = usersStore()

const show = defineModel({ type: Boolean })
const router = useRouter()
const error = ref(null)
const isCreating = ref(false)

const { document: record, triggerOnBeforeCreate } = useDocument(props.doctype)

const statuses = createListResource({
  doctype: config.value.statusDoctype,
  fields: ['name', 'color', 'position', 'type'],
  orderBy: 'position asc',
  cache: `${props.doctype}-statuses`,
  initialData: [],
  auto: true,
  transform(_statuses) {
    for (let status of _statuses) {
      status.color = parseColor(status.color)
    }
    return _statuses
  },
  onSuccess(_statuses) {
    if (!record.doc?.status && _statuses[0]?.name) {
      record.doc.status = _statuses[0].name
    }
  },
})

const statusOptions = computed(() =>
  (statuses.data || []).map((status) => ({ label: status.name, value: status.name })),
)

function getStatusColor(name) {
  return (statuses.data || []).find((status) => status.name === name)?.color
}

const tabs = createResource({
  url: 'crm.fcrm.doctype.crm_fields_layout.crm_fields_layout.get_fields_layout',
  cache: ['QuickEntry', props.doctype],
  params: { doctype: props.doctype, type: 'Quick Entry' },
  auto: true,
  transform: (_tabs) => {
    _tabs.forEach((tab) => {
      tab.sections.forEach((section) => {
        section.columns.forEach((column) => {
          column.fields.forEach((field) => {
            if (field.fieldname == 'status') {
              field.fieldtype = 'Select'
              field.options = statusOptions.value
              field.prefix = getStatusColor(record.doc.status)
            }

            if (field.fieldtype === 'Table') {
              record.doc[field.fieldname] = []
            }
          })
        })
      })
    })
    return _tabs
  },
})

const insertRecord = createResource({
  url: 'frappe.client.insert',
})

async function createRecord() {
  if (record.doc.website && !record.doc.website.startsWith('http')) {
    record.doc.website = 'https://' + record.doc.website
  }

  await triggerOnBeforeCreate?.()

  insertRecord.submit(
    {
      doc: {
        doctype: props.doctype,
        ...record.doc,
      },
    },
    {
      validate() {
        error.value = null
        if (!record.doc.first_name) {
          error.value = __('First Name is mandatory')
          return error.value
        }
        if (record.doc.annual_revenue) {
          if (typeof record.doc.annual_revenue === 'string') {
            record.doc.annual_revenue = record.doc.annual_revenue.replace(
              /,/g,
              '',
            )
          } else if (isNaN(record.doc.annual_revenue)) {
            error.value = __('Annual Revenue should be a number')
            return error.value
          }
        }
        if (
          record.doc.mobile_no &&
          isNaN(record.doc.mobile_no.replace(/[-+() ]/g, ''))
        ) {
          error.value = __('Mobile number should be a number')
          return error.value
        }
        if (record.doc.email && !record.doc.email.includes('@')) {
          error.value = __('Invalid email address')
          return error.value
        }
        if (!record.doc.status) {
          error.value = __('Status is required')
          return error.value
        }
        isCreating.value = true
      },
      onSuccess(data) {
        isCreating.value = false
        show.value = false
        record.doc = {}
        router.push({
          name: config.value.routeName,
          params: { [config.value.routeParam]: data.name },
        })
      },
      onError(err) {
        isCreating.value = false
        if (!err.messages) {
          error.value = err.message
          return
        }
        error.value = err.messages.join('\n')
      },
    },
  )
}

function openQuickEntryModal() {
  showQuickEntryModal.value = true
  quickEntryProps.value = { doctype: props.doctype }
  nextTick(() => (show.value = false))
}

onMounted(() => {
  record.doc.no_of_employees = '1-10'
  Object.assign(record.doc, props.defaults)

  if (!record.doc[config.value.ownerField]) {
    record.doc[config.value.ownerField] = getUser().name
  }
  if (!record.doc.status && statuses.data?.[0]?.name) {
    record.doc.status = statuses.data[0].name
  }
})
</script>
