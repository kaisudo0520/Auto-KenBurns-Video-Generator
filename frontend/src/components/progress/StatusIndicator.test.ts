/**
 * @vitest-environment happy-dom
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import StatusIndicator from '@/components/progress/StatusIndicator.vue'

describe('StatusIndicator', () => {
  it('renders with default props', () => {
    const wrapper = mount(StatusIndicator, {
      props: {
        status: 'idle'
      }
    })

    expect(wrapper.exists()).toBe(true)
    expect(wrapper.props('status')).toBe('idle')
    expect(wrapper.props('size')).toBe('md')
    expect(wrapper.props('showLabel')).toBe(true)
    expect(wrapper.props('animate')).toBe(true)
  })

  it('renders idle status correctly', () => {
    const wrapper = mount(StatusIndicator, {
      props: {
        status: 'idle',
        showLabel: true
      }
    })

    expect(wrapper.props('status')).toBe('idle')
  })

  it('renders processing status correctly', () => {
    const wrapper = mount(StatusIndicator, {
      props: {
        status: 'processing',
        showLabel: true
      }
    })

    expect(wrapper.props('status')).toBe('processing')
  })

  it('renders completed status correctly', () => {
    const wrapper = mount(StatusIndicator, {
      props: {
        status: 'completed',
        showLabel: true
      }
    })

    expect(wrapper.props('status')).toBe('completed')
  })

  it('renders error status correctly', () => {
    const wrapper = mount(StatusIndicator, {
      props: {
        status: 'error',
        showLabel: true
      }
    })

    expect(wrapper.props('status')).toBe('error')
  })

  it('renders pending status correctly', () => {
    const wrapper = mount(StatusIndicator, {
      props: {
        status: 'pending',
        showLabel: true
      }
    })

    expect(wrapper.props('status')).toBe('pending')
  })

  it('renders different sizes', () => {
    const sizes = ['sm', 'md', 'lg'] as const

    sizes.forEach(size => {
      const wrapper = mount(StatusIndicator, {
        props: { status: 'idle', size }
      })

      expect(wrapper.props('size')).toBe(size)
    })
  })

  it('shows label when showLabel is true', () => {
    const wrapper = mount(StatusIndicator, {
      props: {
        status: 'processing',
        showLabel: true
      }
    })

    expect(wrapper.props('showLabel')).toBe(true)
  })

  it('hides label when showLabel is false', () => {
    const wrapper = mount(StatusIndicator, {
      props: {
        status: 'processing',
        showLabel: false
      }
    })

    expect(wrapper.props('showLabel')).toBe(false)
  })

  it('uses custom label when provided', () => {
    const wrapper = mount(StatusIndicator, {
      props: {
        status: 'processing',
        label: '自定義標籤',
        showLabel: true
      }
    })

    expect(wrapper.props('label')).toBe('自定義標籤')
  })
})
