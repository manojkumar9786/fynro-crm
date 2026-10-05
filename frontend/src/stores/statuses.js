import IndicatorIcon from '@/components/Icons/IndicatorIcon.vue'
import { parseColor, isTranslatable } from '@/utils'
import { defineStore } from 'pinia'
import { useTelemetry } from 'frappe-ui/frappe'
import { createListResource } from 'frappe-ui'
import { reactive, h } from 'vue'

export const statusesStore = defineStore('crm-statuses', () => {
  let leadStatusesByName = reactive({})
  let dealStatusesByName = reactive({})
  let prospectStatusesByName = reactive({})
  let customerStatusesByName = reactive({})
  let callingStatusesByName = reactive({})
  let communicationStatusesByName = reactive({})

  const { capture } = useTelemetry()

  const leadStatuses = createListResource({
    doctype: 'CRM Lead Status',
    fields: ['name', 'color', 'position', 'type'],
    orderBy: 'position asc',
    cache: 'lead-statuses',
    initialData: [],
    auto: true,
    transform(statuses) {
      for (let status of statuses) {
        status.color = parseColor(status.color)
        leadStatusesByName[status.name] = status
      }
      return statuses
    },
  })

  const dealStatuses = createListResource({
    doctype: 'CRM Deal Status',
    fields: ['name', 'color', 'position', 'type'],
    orderBy: 'position asc',
    cache: 'deal-statuses',
    initialData: [],
    auto: true,
    transform(statuses) {
      for (let status of statuses) {
        status.color = parseColor(status.color)
        dealStatusesByName[status.name] = status
      }
      return statuses
    },
  })

  const prospectStatuses = createListResource({
    doctype: 'CRM Prospect Status',
    fields: ['name', 'color', 'position', 'type'],
    orderBy: 'position asc',
    cache: 'prospect-statuses',
    initialData: [],
    auto: true,
    transform(statuses) {
      for (let status of statuses) {
        status.color = parseColor(status.color)
        prospectStatusesByName[status.name] = status
      }
      return statuses
    },
  })

  const customerStatuses = createListResource({
    doctype: 'CRM Customer Status',
    fields: ['name', 'color', 'position', 'type'],
    orderBy: 'position asc',
    cache: 'customer-statuses',
    initialData: [],
    auto: true,
    transform(statuses) {
      for (let status of statuses) {
        status.color = parseColor(status.color)
        customerStatusesByName[status.name] = status
      }
      return statuses
    },
  })

  const callingStatuses = createListResource({
    doctype: 'CRM Calling Status',
    fields: ['name', 'color', 'position', 'type'],
    orderBy: 'position asc',
    cache: 'calling-statuses',
    initialData: [],
    auto: true,
    transform(statuses) {
      for (let status of statuses) {
        status.color = parseColor(status.color)
        callingStatusesByName[status.name] = status
      }
      return statuses
    },
  })

  const communicationStatuses = createListResource({
    doctype: 'CRM Communication Status',
    fields: ['name'],
    cache: 'communication-statuses',
    initialData: [],
    auto: true,
    transform(statuses) {
      for (let status of statuses) {
        communicationStatusesByName[status.name] = status
      }
      return statuses
    },
  })

  function getLeadStatus(name) {
    if (!name) {
      name = leadStatuses.data[0].name
    }
    return leadStatusesByName[name]
  }

  function getDealStatus(name) {
    if (!name) {
      name = dealStatuses.data[0].name
    }
    return dealStatusesByName[name]
  }

  function getProspectStatus(name) {
    if (!name) {
      name = prospectStatuses.data[0].name
    }
    return prospectStatusesByName[name]
  }

  function getCustomerStatus(name) {
    if (!name) {
      name = customerStatuses.data[0].name
    }
    return customerStatusesByName[name]
  }

  function getCallingStatus(name) {
    if (!name) return null
    return callingStatusesByName[name]
  }

  function getCommunicationStatus(name) {
    if (!name) {
      name = communicationStatuses.data[0].name
    }
    return communicationStatuses[name]
  }

  function statusOptions(doctype, statuses = [], triggerStatusChange = null) {
    const statusMaps = {
      lead: [leadStatusesByName, 'CRM Lead Status'],
      deal: [dealStatusesByName, 'CRM Deal Status'],
      prospect: [prospectStatusesByName, 'CRM Prospect Status'],
      customer: [customerStatusesByName, 'CRM Customer Status'],
      calling: [callingStatusesByName, 'CRM Calling Status'],
    }
    const [allStatusesByName, statusDoctype] =
      statusMaps[doctype] || statusMaps.lead
    let statusesByName = allStatusesByName

    if (statuses?.length) {
      statusesByName = statuses.reduce((acc, status) => {
        acc[status] = statusesByName[status]
        return acc
      }, {})
    }

    let translatable = isTranslatable(statusDoctype)

    let options = []
    for (const status in statusesByName) {
      options.push({
        label: translatable
          ? __(statusesByName[status]?.name)
          : statusesByName[status]?.name,
        value: statusesByName[status]?.name,
        icon: () => h(IndicatorIcon, { class: statusesByName[status]?.color }),
        onClick: async () => {
          await triggerStatusChange?.(statusesByName[status]?.name)
          capture('status_changed', { doctype, status })
        },
      })
    }
    return options
  }

  return {
    leadStatuses,
    dealStatuses,
    prospectStatuses,
    customerStatuses,
    callingStatuses,
    communicationStatuses,
    getLeadStatus,
    getDealStatus,
    getProspectStatus,
    getCustomerStatus,
    getCallingStatus,
    getCommunicationStatus,
    statusOptions,
  }
})
