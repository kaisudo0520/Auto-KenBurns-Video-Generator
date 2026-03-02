/**
 * @vitest-environment happy-dom
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ProgressBar from '@/components/progress/ProgressBar.vue'

describe('ProgressBar', () => {
  it('renders with default props', () => {
    const wrapper = mount(ProgressBar, {
      props: {
        value: 50
      }
    })

    expect(wrapper.exists()).toBe(true)
    expect(wrapper.props('value')).toBe(50)
    expect(wrapper.props('max')).toBe(100)
    expect(wrapper.props('size')).toBe('md')
    expect(wrapper.props('variant')).toBe('gradient')
  })

  it('calculates percentage correctly', () => {
    const wrapper = mount(ProgressBar, {
      props: {
        value: 25,
        max: 100
      }
    })

    expect(wrapper.vm.percent).toBe(25)
  })

  it('clamps percentage between 0 and 100', () => {
    const wrapper = mount(ProgressBar, {
      props: {
        value: 150,
        max: 100
      }
    })

    expect(wrapper.vm.percent).toBe(100)
  })

  it('handles negative values', () => {
    const wrapper = mount(ProgressBar, {
      props: {
        value: -10,
        max: 100
      }
    })

    expect(wrapper.vm.percent).toBe(0)
  })

  it('renders different sizes', () => {
    const sizes = ['sm', 'md', 'lg'] as const

    sizes.forEach(size => {
      const wrapper = mount(ProgressBar, {
        props: { value: 50, size }
      })

      expect(wrapper.props('size')).toBe(size)
    })
  })

  it('renders different variants', () => {
    const variants = ['default', 'gradient', 'success', 'warning', 'error'] as const

    variants.forEach(variant => {
      const wrapper = mount(ProgressBar, {
        props: { value: 50, variant }
      })

      expect(wrapper.props('variant')).toBe(variant)
    })
  })

  it('shows label when showLabel is true', () => {
    const wrapper = mount(ProgressBar, {
      props: {
        value: 50,
        showLabel: true
      }
    })

    expect(wrapper.props('showLabel')).toBe(true)
    expect(wrapper.text()).toContain('50%')
  })

  it('hides label when showLabel is false', () => {
    const wrapper = mount(ProgressBar, {
      props: {
        value: 50,
        showLabel: false
      }
    })

    expect(wrapper.props('showLabel')).toBe(false)
  })
})
