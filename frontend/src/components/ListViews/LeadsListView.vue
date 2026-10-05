<template>
  <ListView
    :class="$attrs.class"
    :columns="columns"
    :rows="rows"
    :options="{
      getRowRoute: (row) => ({
        name: detailRouteName,
        params: { leadId: row.name },
        query: { view: route.query.view, viewType: route.params.viewType },
      }),
      selectable: options.selectable,
      showTooltip: options.showTooltip,
      resizeColumn: options.resizeColumn,
    }"
    row-key="name"
    @update:selections="(selections) => emit('selectionsChanged', selections)"
  >
    <ListHeader
      class="sm:mx-5 mx-3"
      @columnWidthUpdated="emit('columnWidthUpdated')"
    >
      <ListHeaderItem
        v-for="column in columns"
        :key="column.key"
        :item="column"
        @columnWidthUpdated="(e) => onColumnWidthUpdated(e, column)"
      >
        <Button
          v-if="column.key == '_liked_by'"
          variant="ghost"
          class="!h-4"
          @click="() => emit('applyLikeFilter')"
        >
          <HeartIcon
            class="h-4 w-4"
            :class="isLikeFilterApplied ? 'fill-red-500 text-red-500' : ''"
          />
        </Button>
      </ListHeaderItem>
    </ListHeader>
    <ListRows
      v-slot="{ idx, column, item, row }"
      :rows="rows"
      doctype="CRM Lead"
    >
      <ListRowItem :item="item" :align="column.align" class="overflow-hidden">
        <template #prefix>
          <div
            v-if="column.key === '_assign'"
            class="flex items-center truncate"
          >
            <MultipleAvatar
              :avatars="item"
              size="sm"
              @click="
                (event) =>
                  emit('applyFilter', {
                    event,
                    idx,
                    column,
                    item,
                    firstColumn: columns[0],
                  })
              "
            />
          </div>
          <div v-else-if="column.key === 'lead_name'">
            <Avatar
              v-if="item.label"
              class="flex items-center"
              :image="item.image"
              :label="item.image_label"
              size="sm"
            />
          </div>
          <div v-else-if="column.key === 'lead_owner'">
            <Avatar
              v-if="item.full_name"
              class="flex items-center"
              :image="item.user_image"
              :label="item.full_name"
              size="sm"
            />
          </div>
          <div v-else-if="column.key === 'mobile_no' && item">
            <PhoneIcon class="h-4 w-4" />
          </div>
        </template>
        <template #default="{ label }">
          <div
            v-if="
              [
                'modified',
                'creation',
                'first_response_time',
                'first_responded_on',
                'response_by',
              ].includes(column.key)
            "
            class="truncate text-base"
            @click="
              (event) =>
                emit('applyFilter', {
                  event,
                  idx,
                  column,
                  item,
                  firstColumn: columns[0],
                })
            "
          >
            <Tooltip :text="item.label">
              <div>{{ item.timeAgo }}</div>
            </Tooltip>
          </div>
          <div v-else-if="column.key === '_liked_by'">
            <Button
              variant="ghost"
              @click.stop.prevent="
                () =>
                  emit('likeDoc', {
                    name: row.name,
                    liked: isLiked(item),
                  })
              "
            >
              <HeartIcon
                class="h-4 w-4"
                :class="isLiked(item) ? 'fill-red-500 text-red-500' : ''"
              />
            </Button>
          </div>
          <div
            v-else-if="column.key === 'sla_status'"
            class="truncate text-base"
          >
            <Badge
              v-if="item.value"
              :variant="'subtle'"
              :theme="item.color"
              size="md"
              :label="item.value"
              @click="
                (event) =>
                  emit('applyFilter', {
                    event,
                    idx,
                    column,
                    item,
                    firstColumn: columns[0],
                  })
              "
            />
          </div>
          <div v-else-if="column.type === 'Check'">
            <FormControl
              type="checkbox"
              :modelValue="item"
              :disabled="true"
              class="text-ink-gray-9"
            />
          </div>
          <RatingInput
            v-else-if="column.type === 'Rating'"
            :value="item"
            class="!opacity-100 flex-nowrap overflow-auto"
            :disabled="true"
            :max="column.options || 5"
            @click="
              (event) =>
                emit('applyFilter', {
                  event,
                  idx,
                  column,
                  item,
                  firstColumn: columns[0],
                })
            "
          />
          <div
            v-else-if="isStatusColumn(column.key)"
            class="min-w-0 max-w-full truncate text-base"
            @click.stop
          >
            <Dropdown
              :options="getStatusOptions(row, column.key)"
              placement="bottom-start"
            >
              <template #default="{ open }">
                <Button
                  variant="ghost"
                  size="sm"
                  class="-ml-1.5 min-w-0 max-w-full"
                  :label="getLabel(label, column) || '—'"
                  :iconRight="open ? 'chevron-up' : 'chevron-down'"
                  @click.stop.prevent
                >
                  <template #prefix>
                    <IndicatorIcon :class="item.color" />
                  </template>
                </Button>
              </template>
            </Dropdown>
          </div>
          <div
            v-else-if="label"
            class="truncate text-base"
            @click="
              (event) =>
                emit('applyFilter', {
                  event,
                  idx,
                  column,
                  item,
                  firstColumn: columns[0],
                })
            "
          >
            {{ getLabel(label, column) }}
          </div>
        </template>
      </ListRowItem>
    </ListRows>
    <ListSelectBanner>
      <template #actions="{ selections, unselectAll }">
        <Dropdown
          :options="listBulkActionsRef.bulkActions(selections, unselectAll)"
        >
          <Button icon="lucide-more-horizontal" variant="ghost" />
        </Dropdown>
      </template>
    </ListSelectBanner>
  </ListView>
  <ListFooter
    v-if="pageLengthCount"
    v-model="pageLengthCount"
    class="border-t sm:px-5 px-3 py-2"
    :options="{
      rowCount: options.rowCount,
      totalCount: options.totalCount,
    }"
    @loadMore="emit('loadMore')"
  />
  <ListBulkActions ref="listBulkActionsRef" v-model="list" doctype="CRM Lead" />
</template>

<script setup>
import HeartIcon from '@/components/Icons/HeartIcon.vue'
import IndicatorIcon from '@/components/Icons/IndicatorIcon.vue'
import PhoneIcon from '@/components/Icons/PhoneIcon.vue'
import RatingInput from '@/components/Controls/RatingInput.vue'
import MultipleAvatar from '@/components/MultipleAvatar.vue'
import ListBulkActions from '@/components/ListBulkActions.vue'
import ListRows from '@/components/ListViews/ListRows.vue'
import { isTranslatable, formatDuration } from '@/utils'
import {
  Avatar,
  ListView,
  ListHeader,
  ListHeaderItem,
  ListSelectBanner,
  ListRowItem,
  ListFooter,
  Dropdown,
  Tooltip,
  call,
  toast,
} from 'frappe-ui'
import { sessionStore } from '@/stores/session'
import { statusesStore } from '@/stores/statuses'
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'

const props = defineProps({
  rows: { type: Array, required: true },
  columns: { type: Array, required: true },
  detailRouteName: { type: String, default: 'Lead' },
  options: {
    type: Object,
    default: () => ({
      selectable: true,
      showTooltip: true,
      resizeColumn: false,
      totalCount: 0,
      rowCount: 0,
    }),
  },
})
const emit = defineEmits([
  'loadMore',
  'updatePageCount',
  'columnWidthUpdated',
  'applyFilter',
  'applyLikeFilter',
  'likeDoc',
  'selectionsChanged',
])

const route = useRoute()

const pageLengthCount = defineModel({ type: Number })
const list = defineModel('list', { type: Object })

function onColumnWidthUpdated({ width, save }, column) {
  column.width = width
  if (save) emit('columnWidthUpdated', column)
}

function getLabel(label, column) {
  if (column.type === 'Duration') return formatDuration(label)
  if (column.options && isTranslatable(column.options)) return __(label)
  return label
}

const isLikeFilterApplied = computed(() => {
  return list.value.params?.filters?._liked_by ? true : false
})

const { user } = sessionStore()
const { statusOptions } = statusesStore()

// Columns that are status-type Link fields get an inline, click-to-change
// dropdown in the list (instead of opening the record) — "status" is the
// main Lead Status, "calling_status" the call-outcome sub-status.
const STATUS_COLUMN_DOCTYPE_KEY = { status: 'lead', calling_status: 'calling' }

function isStatusColumn(key) {
  return Object.hasOwn(STATUS_COLUMN_DOCTYPE_KEY, key)
}

function getStatusOptions(row, fieldname) {
  return statusOptions(STATUS_COLUMN_DOCTYPE_KEY[fieldname], [], (value) =>
    updateRowStatus(row, fieldname, value),
  )
}

async function updateRowStatus(row, fieldname, value) {
  try {
    await call('frappe.client.set_value', {
      doctype: 'CRM Lead',
      name: row.name,
      fieldname,
      value,
    })
    list.value?.reload?.()
  } catch (err) {
    toast.error(err.messages?.[0] || __('Error updating status'))
  }
}

function isLiked(item) {
  if (item) {
    let likedByMe = JSON.parse(item)
    return likedByMe.includes(user)
  }
}

watch(pageLengthCount, (val, old_value) => {
  if (val === old_value) return
  emit('updatePageCount', val)
})

const listBulkActionsRef = ref(null)

defineExpose({
  customListActions: computed(
    () => listBulkActionsRef.value?.customListActions,
  ),
})
</script>
